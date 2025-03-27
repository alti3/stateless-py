from typing import (
    TypeVar,
    Generic,
    Optional,
    Sequence,
    Any,
    List,
    Callable,
    cast,
    Tuple,
    Awaitable,
    Union,
)
from abc import ABC, abstractmethod
import inspect
import asyncio

from .guards import TransitionGuard, EMPTY_GUARD
from .transition import StateT, TriggerT, Transition
from .reflection import (
    InvocationInfo,
    DynamicStateInfo,
    DynamicStateInfos,
    TriggerInfo,
    GuardInfo,
)
from .exceptions import ConfigurationError
from .actions import ActionFuncResult, _build_wrapper

Args = Sequence[Any]
DestinationStateSelector = Callable[..., Union[StateT, Awaitable[StateT]]]


class TriggerBehaviourResult(Generic[StateT, TriggerT]):
    """Result of finding a trigger handler, indicating success or unmet guards."""

    def __init__(
        self,
        handler: Optional["TriggerBehaviour[StateT, TriggerT]"],
        unmet_guard_conditions: List[str],
    ):
        self._handler = handler
        self._unmet_guard_conditions = unmet_guard_conditions

    @property
    def handler(self) -> Optional["TriggerBehaviour[StateT, TriggerT]"]:
        """The trigger behaviour that handles the trigger (if guards are met)."""
        return self._handler

    @property
    def unmet_guard_conditions(self) -> List[str]:
        """Descriptions of guards that were not met."""
        return self._unmet_guard_conditions

    @property
    def guards_met(self) -> bool:
        """True if a handler was found and all its guards were met."""
        return self._handler is not None and not self._unmet_guard_conditions


class TriggerBehaviour(ABC, Generic[StateT, TriggerT]):
    """Base class for defining behavior associated with a trigger within a state."""

    def __init__(self, trigger: TriggerT, guard: TransitionGuard):
        self._trigger = trigger
        self._guard = guard

    @property
    def trigger(self) -> TriggerT:
        """The trigger this behaviour is associated with."""
        return self._trigger

    @property
    def guard(self) -> TransitionGuard:
        """The guards that must be met for this behaviour to be active."""
        return self._guard

    @abstractmethod
    def results_in_transition_from(
        self, source: StateT, args: Args
    ) -> Awaitable[Tuple[bool, Optional[StateT]]]:
        """
        Determines if this behaviour results in a transition from the given source state.

        Returns:
            A tuple (results_in_transition, destination_state).
            `results_in_transition` is True if the trigger applies and guards pass.
            `destination_state` is the target state if it results in a transition, otherwise None.
        """
        pass

    @abstractmethod
    def get_trigger_info(self) -> TriggerInfo:
        """Gets reflection info for the trigger."""
        pass

    @abstractmethod
    def get_guard_info(self) -> List[GuardInfo]:
        """Gets reflection info for the guards."""
        pass


class IgnoredTriggerBehaviour(TriggerBehaviour[StateT, TriggerT]):
    """A trigger behaviour that explicitly ignores the trigger."""

    def __init__(self, trigger: TriggerT, guard: TransitionGuard):
        super().__init__(trigger, guard)

    async def results_in_transition_from(
        self, source: StateT, args: Args
    ) -> Tuple[bool, Optional[StateT]]:
        # Ignored transitions never result in a state change
        guards_met = await self.guard.conditions_met_async(args)
        return (
            guards_met,
            None,
        )  # True if guards met (meaning ignore applies), but no destination

    def get_trigger_info(self) -> TriggerInfo:
        # Assuming TriggerInfo can be created from just the trigger value
        # Parameter types might be unknown here unless explicitly provided during config
        return TriggerInfo(underlying_trigger=self.trigger)

    def get_guard_info(self) -> List[GuardInfo]:
        return [
            GuardInfo(method_description=g.method_description)
            for g in self.guard.conditions
        ]


class ReentryTriggerBehaviour(TriggerBehaviour[StateT, TriggerT]):
    """A trigger behaviour that causes a reentry into the source state."""

    def __init__(self, trigger: TriggerT, guard: TransitionGuard, destination: StateT):
        super().__init__(trigger, guard)
        self._destination = destination  # This is the source state itself

    @property
    def destination(self) -> StateT:
        return self._destination

    async def results_in_transition_from(
        self, source: StateT, args: Args
    ) -> Tuple[bool, Optional[StateT]]:
        if source != self.destination:
            # This shouldn't happen if configured correctly, but as a safeguard
            raise ConfigurationError(
                f"Reentry behaviour configured for trigger {self.trigger} expects source {self.destination} but got {source}"
            )
        guards_met = await self.guard.conditions_met_async(args)
        return guards_met, self.destination if guards_met else None

    def get_trigger_info(self) -> TriggerInfo:
        return TriggerInfo(underlying_trigger=self.trigger)

    def get_guard_info(self) -> List[GuardInfo]:
        return [
            GuardInfo(method_description=g.method_description)
            for g in self.guard.conditions
        ]


class InternalTriggerBehaviour(TriggerBehaviour[StateT, TriggerT]):
    """A trigger behaviour that executes actions but does not cause a state change (internal transition)."""

    def __init__(
        self,
        trigger: TriggerT,
        guard: TransitionGuard,
        action: Callable[..., ActionFuncResult],
        description: Optional[str] = None,
    ):
        super().__init__(trigger, guard)
        self._invocation_info = InvocationInfo.from_callable(action, description)
        # Wrap the action to handle arguments (transition, args_tuple) like entry actions
        # Internal actions also receive the transition and trigger args
        self._wrapped_action = _build_wrapper(
            action, ["transition", "args"], self._invocation_info.is_async
        )

    @property
    def action_info(self) -> InvocationInfo:
        return self._invocation_info

    async def results_in_transition_from(
        self, source: StateT, args: Args
    ) -> Tuple[bool, Optional[StateT]]:
        # Internal transitions don't change state, but guards must pass for action to run
        guards_met = await self.guard.conditions_met_async(args)
        # An internal transition is still considered a "result" if guards pass,
        # but the destination is None (or source, depending on interpretation).
        # Let's return (True, None) to signify the trigger was handled internally.
        return guards_met, None

    async def execute_internal_action(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> None:
        """Executes the internal action associated with this behaviour."""
        if self._invocation_info.is_async:
            # Cast needed because _build_wrapper returns a generic callable
            async_wrapped = cast(
                Callable[[Transition[StateT, TriggerT], Args], Awaitable[None]],
                self._wrapped_action,
            )
            await async_wrapped(transition, args)
        else:
            sync_wrapped = cast(
                Callable[[Transition[StateT, TriggerT], Args], None],
                self._wrapped_action,
            )
            # Check if the sync action is being called in an async context (fire_async)
            # If so, it's fine. If called from sync fire(), raise TypeError if action was async.
            # The check for async guard/action should happen in StateMachine.fire
            sync_wrapped(transition, args)

    def get_trigger_info(self) -> TriggerInfo:
        # TODO: Infer parameter types from action signature?
        return TriggerInfo(underlying_trigger=self.trigger)

    def get_guard_info(self) -> List[GuardInfo]:
        return [
            GuardInfo(method_description=g.method_description)
            for g in self.guard.conditions
        ]


class TransitioningTriggerBehaviour(TriggerBehaviour[StateT, TriggerT]):
    """A trigger behaviour that transitions to a fixed destination state."""

    def __init__(self, trigger: TriggerT, destination: StateT, guard: TransitionGuard):
        super().__init__(trigger, guard)
        self._destination = destination

    @property
    def destination(self) -> StateT:
        return self._destination

    async def results_in_transition_from(
        self, source: StateT, args: Args
    ) -> Tuple[bool, Optional[StateT]]:
        guards_met = await self.guard.conditions_met_async(args)
        return guards_met, self.destination if guards_met else None

    def get_trigger_info(self) -> TriggerInfo:
        return TriggerInfo(underlying_trigger=self.trigger)

    def get_guard_info(self) -> List[GuardInfo]:
        return [
            GuardInfo(method_description=g.method_description)
            for g in self.guard.conditions
        ]


class DynamicTriggerBehaviour(TriggerBehaviour[StateT, TriggerT]):
    """A trigger behaviour that transitions to a dynamically determined destination state."""

    def __init__(
        self,
        trigger: TriggerT,
        destination_func: DestinationStateSelector,
        guard: TransitionGuard,
        description: Optional[str] = None,  # Added description parameter
    ):
        super().__init__(trigger, guard)
        self._destination_func = destination_func
        # Use provided description for InvocationInfo
        self._invocation_info = InvocationInfo.from_callable(
            destination_func, description
        )
        # Wrap the selector function to handle arguments passed via fire()
        # Dynamic selectors receive the trigger args directly
        self._wrapped_selector = _build_wrapper(
            destination_func, ["args"], self._invocation_info.is_async
        )

    @property
    def destination_func_info(self) -> InvocationInfo:
        return self._invocation_info

    async def _get_destination_async(self, args: Args) -> StateT:
        """Calls the destination function, handling sync/async and arguments."""
        # Use the wrapped selector
        if self._invocation_info.is_async:
            async_wrapped = cast(
                Callable[[Args], Awaitable[StateT]], self._wrapped_selector
            )
            return await async_wrapped(args)
        else:
            sync_wrapped = cast(Callable[[Args], StateT], self._wrapped_selector)
            # Allow calling sync selector from async context
            return sync_wrapped(args)

    async def results_in_transition_from(
        self, source: StateT, args: Args
    ) -> Tuple[bool, Optional[StateT]]:
        guards_met = await self.guard.conditions_met_async(args)
        if not guards_met:
            return False, None
        try:
            destination = await self._get_destination_async(args)
            return True, destination
        except Exception:
            # Decide how to handle exceptions in the dynamic selector
            # C# seems to let them bubble up.
            raise

    def get_trigger_info(self) -> TriggerInfo:
        # TODO: Infer parameter types from selector signature?
        return TriggerInfo(underlying_trigger=self.trigger)

    def get_guard_info(self) -> List[GuardInfo]:
        return [
            GuardInfo(method_description=g.method_description)
            for g in self.guard.conditions
        ]


# TODO: Add ParameterizedTriggerBehaviour if needed, or handle parameter types within existing behaviours.
