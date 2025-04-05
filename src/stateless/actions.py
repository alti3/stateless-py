import inspect
from typing import (
    Any,
    Generic,
    cast
)
from abc import ABC, abstractmethod
from collections.abc import Sequence, Callable, Awaitable

from .reflection import InvocationInfo, ActionDef
from .transition import Transition, StateT, TriggerT
from .exceptions import ConfigurationError

Args = Sequence[Any]
ActionFuncResult = None | Awaitable[None]
ActionFunc = Callable[..., ActionFuncResult]


# --- Base Action Behaviour ---
class ActionBehaviour(ABC, Generic[StateT, TriggerT]):
    """Base class for all action behaviours (entry, exit, activate, deactivate)."""

    def __init__(self, description: InvocationInfo):
        self._description = description

    @property
    def description(self) -> InvocationInfo:
        """Detailed information about the action function."""
        return self._description

    @abstractmethod
    def execute(self, *args: Any) -> None:
        """Executes the action synchronously."""
        pass

    @abstractmethod
    async def execute_async(self, *args: Any) -> None:
        """Executes the action, allowing for async actions."""
        pass


# --- Entry Action ---
class EntryActionBehaviour(ActionBehaviour[StateT, TriggerT]):
    """Base for actions executed when entering a state."""

    @abstractmethod
    def execute(self, transition: Transition[StateT, TriggerT], args: Args) -> None:  # type: ignore[override]
        pass

    @abstractmethod
    async def execute_async(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> None:  # type: ignore[override]
        pass


class SyncEntryAction(EntryActionBehaviour[StateT, TriggerT]):
    """Synchronous entry action."""

    def __init__(
        self,
        action: Callable[[Transition[StateT, TriggerT], Args], None],
        description: InvocationInfo,
    ):
        super().__init__(description)
        self._action = action

    def execute(self, transition: Transition[StateT, TriggerT], args: Args) -> None:
        self._action(transition, args)

    async def execute_async(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> None:
        self.execute(transition, args)  # Execute sync action directly


class AsyncEntryAction(EntryActionBehaviour[StateT, TriggerT]):
    """Asynchronous entry action."""

    def __init__(
        self,
        action: Callable[[Transition[StateT, TriggerT], Args], Awaitable[None]],
        description: InvocationInfo,
    ):
        super().__init__(description)
        self._action = action

    def execute(self, transition: Transition[StateT, TriggerT], args: Args) -> None:
        raise TypeError(
            f"Cannot execute async entry action '{self.description.method_name or '<lambda>'}' synchronously."
        )

    async def execute_async(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> None:
        await self._action(transition, args)


class EntryActionBehaviorFromTrigger(EntryActionBehaviour[StateT, TriggerT]):
    """Entry action that only executes if the transition was caused by a specific trigger."""

    def __init__(
        self,
        trigger: TriggerT,
        action_behaviour: EntryActionBehaviour[StateT, TriggerT],
    ):
        # Use the inner action's description, but perhaps add context?
        desc = f"{action_behaviour.description.description} (when triggered by {trigger!r})"
        inv_info = InvocationInfo(
            method_name=action_behaviour.description.method_name,
            description=desc,
            is_async=action_behaviour.description.is_async,
        )
        super().__init__(inv_info)
        self._trigger = trigger
        self._action_behaviour = action_behaviour

    @property
    def trigger(self) -> TriggerT:
        """The specific trigger required for this action to execute."""
        return self._trigger

    def execute(self, transition: Transition[StateT, TriggerT], args: Args) -> None:
        if transition.trigger == self._trigger:
            self._action_behaviour.execute(transition, args)

    async def execute_async(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> None:
        if transition.trigger == self._trigger:
            await self._action_behaviour.execute_async(transition, args)


# --- Exit Action ---
class ExitActionBehaviour(ActionBehaviour[StateT, TriggerT]):
    """Base for actions executed when exiting a state."""

    # Exit actions in C# only take Transition, not args
    @abstractmethod
    def execute(self, transition: Transition[StateT, TriggerT]) -> None:  # type: ignore[override]
        pass

    @abstractmethod
    async def execute_async(self, transition: Transition[StateT, TriggerT]) -> None:  # type: ignore[override]
        pass


class SyncExitAction(ExitActionBehaviour[StateT, TriggerT]):
    """Synchronous exit action."""

    def __init__(
        self,
        action: Callable[[Transition[StateT, TriggerT]], None],
        description: InvocationInfo,
    ):
        super().__init__(description)
        self._action = action

    def execute(self, transition: Transition[StateT, TriggerT]) -> None:
        self._action(transition)

    async def execute_async(self, transition: Transition[StateT, TriggerT]) -> None:
        self.execute(transition)


class AsyncExitAction(ExitActionBehaviour[StateT, TriggerT]):
    """Asynchronous exit action."""

    def __init__(
        self,
        action: Callable[[Transition[StateT, TriggerT]], Awaitable[None]],
        description: InvocationInfo,
    ):
        super().__init__(description)
        self._action = action

    def execute(self, transition: Transition[StateT, TriggerT]) -> None:
        raise TypeError(
            f"Cannot execute async exit action '{self.description.method_name or '<lambda>'}' synchronously."
        )

    async def execute_async(self, transition: Transition[StateT, TriggerT]) -> None:
        await self._action(transition)


# --- Activate / Deactivate Actions (simplified, no args) ---
class ActivateActionBehaviour(ActionBehaviour[StateT, TriggerT]):
    """Base for actions executed when a state is activated."""

    @abstractmethod
    def execute(self) -> None:  # type: ignore[override]
        pass

    @abstractmethod
    async def execute_async(self) -> None:  # type: ignore[override]
        pass


class SyncActivateAction(ActivateActionBehaviour[StateT, TriggerT]):
    """Synchronous activate action."""

    def __init__(self, action: Callable[[], None], description: InvocationInfo):
        super().__init__(description)
        self._action = action

    def execute(self) -> None:
        self._action()

    async def execute_async(self) -> None:
        self.execute()


class AsyncActivateAction(ActivateActionBehaviour[StateT, TriggerT]):
    """Asynchronous activate action."""

    def __init__(
        self, action: Callable[[], Awaitable[None]], description: InvocationInfo
    ):
        super().__init__(description)
        self._action = action

    def execute(self) -> None:
        raise TypeError("Cannot execute async activate action synchronously.")

    async def execute_async(self) -> None:
        await self._action()


class DeactivateActionBehaviour(ActionBehaviour[StateT, TriggerT]):
    """Base for actions executed when a state is deactivated."""

    @abstractmethod
    def execute(self) -> None:
        pass  # type: ignore[override]

    @abstractmethod
    async def execute_async(self) -> None:
        pass  # type: ignore[override]


class SyncDeactivateAction(DeactivateActionBehaviour[StateT, TriggerT]):
    """Synchronous deactivate action."""

    def __init__(self, action: Callable[[], None], description: InvocationInfo):
        super().__init__(description)
        self._action = action

    def execute(self) -> None:
        self._action()

    async def execute_async(self) -> None:
        self.execute()


class AsyncDeactivateAction(DeactivateActionBehaviour[StateT, TriggerT]):
    """Asynchronous deactivate action."""

    def __init__(
        self, action: Callable[[], Awaitable[None]], description: InvocationInfo
    ):
        super().__init__(description)
        self._action = action

    def execute(self) -> None:
        raise TypeError("Cannot execute async deactivate action synchronously.")

    async def execute_async(self) -> None:
        await self._action()


# --- Parameter Conversion and Factory Helpers ---


def _get_action_and_description(
    action_def: ActionDef,
) -> tuple[Callable, str | None]:
    """Extracts the callable and optional description from ActionDef."""
    if isinstance(action_def, tuple):
        if (
            len(action_def) == 2
            and callable(action_def[0])
            and isinstance(action_def[1], (str, type(None)))
        ):
            return action_def[0], action_def[1]
        else:
            raise ValueError(
                "Invalid ActionDef tuple format. Expected (callable, Optional[str])."
            )
    elif callable(action_def):
        return action_def, None
    else:
        raise TypeError(
            "Action definition must be a callable or a (callable, description) tuple."
        )


def _build_wrapper(
    action: Callable, expected_args: list[str], is_async: bool
) -> Callable[..., ActionFuncResult]:
    """Builds a wrapper function to adapt the user's action callable to the expected signature."""
    sig = inspect.signature(action)
    params = list(sig.parameters.values())
    param_names = list(sig.parameters.keys())
    has_varargs = any(p.kind == p.VAR_POSITIONAL for p in params)

    # Determine which of the expected args the action actually accepts
    accepted_args_indices = []
    for i, arg_name in enumerate(expected_args):
        if arg_name in param_names:
            accepted_args_indices.append(i)
        elif f"_{arg_name}" in param_names:  # Allow private-like names e.g. _transition
            accepted_args_indices.append(i)
        # Basic check for type hints (less reliable)
        # elif any(p.annotation == expected_types[i] for p in params if p.annotation != inspect.Parameter.empty):
        #     accepted_args_indices.append(i)

    num_required_params = len(
        [
            p
            for p in params
            if p.kind == p.POSITIONAL_OR_KEYWORD and p.default == p.empty
        ]
    )

    # If the function takes *args, assume it can handle all expected args it doesn't explicitly name.
    # This is a simplification.
    if has_varargs:
        # Pass only the explicitly named args first, then the rest if *args exists
        explicit_indices = [
            i for i, name in enumerate(expected_args) if name in param_names
        ]
        vararg_indices = [
            i for i, name in enumerate(expected_args) if name not in param_names
        ]

        if is_async:

            async def async_vararg_wrapper(*all_args: Any) -> None:
                call_args = [all_args[i] for i in explicit_indices]
                call_args.extend(all_args[i] for i in vararg_indices)
                await action(*call_args)

            return async_vararg_wrapper
        else:

            def sync_vararg_wrapper(*all_args: Any) -> None:
                call_args = [all_args[i] for i in explicit_indices]
                call_args.extend(all_args[i] for i in vararg_indices)
                action(*call_args)

            return sync_vararg_wrapper

    # If not using *args, only pass the accepted arguments
    elif len(accepted_args_indices) >= num_required_params:
        if is_async:

            async def async_wrapper(*all_args: Any) -> None:
                call_args = [all_args[i] for i in accepted_args_indices]
                await action(*call_args)

            return async_wrapper
        else:

            def sync_wrapper(*all_args: Any) -> None:
                call_args = [all_args[i] for i in accepted_args_indices]
                action(*call_args)

            return sync_wrapper
    else:
        # Not enough expected args match the function signature without *args
        # This case might indicate a configuration error, but we create a wrapper that will likely fail at runtime.
        # Or we could raise a ConfigurationError here. Let's raise.
        action_name = getattr(action, "__name__", "<lambda>")
        raise ConfigurationError(
            f"Action '{action_name}' signature {sig} is incompatible with expected arguments ({', '.join(expected_args)}). "
            f"It requires {num_required_params} arguments but only {len(accepted_args_indices)} could be mapped."
        )


def create_entry_action_behavior(
    action_def: ActionDef, trigger: TriggerT | None = None
) -> EntryActionBehaviour[StateT, TriggerT]:
    """Factory to create sync/async entry action behaviors."""
    action, description_override = _get_action_and_description(action_def)
    invocation_info = InvocationInfo.from_callable(action, description_override)
    is_async = invocation_info.is_async

    # Entry actions expect (transition, args_tuple)
    wrapped_action = _build_wrapper(action, ["transition", "args"], is_async)

    action_behavior: EntryActionBehaviour[StateT, TriggerT]
    if is_async:
        # Cast needed because _build_wrapper returns a generic callable
        async_wrapped = cast(
            Callable[[Transition[StateT, TriggerT], Args], Awaitable[None]],
            wrapped_action,
        )
        action_behavior = AsyncEntryAction(async_wrapped, invocation_info)
    else:
        sync_wrapped = cast(
            Callable[[Transition[StateT, TriggerT], Args], None], wrapped_action
        )
        action_behavior = SyncEntryAction(sync_wrapped, invocation_info)

    if trigger is not None:
        action_behavior = EntryActionBehaviorFromTrigger(trigger, action_behavior)

    return action_behavior


def create_exit_action_behavior(
    action_def: ActionDef,
) -> ExitActionBehaviour[StateT, TriggerT]:
    """Factory to create sync/async exit action behaviors."""
    action, description_override = _get_action_and_description(action_def)
    invocation_info = InvocationInfo.from_callable(action, description_override)
    is_async = invocation_info.is_async

    # Exit actions expect only (transition)
    wrapped_action = _build_wrapper(action, ["transition"], is_async)

    if is_async:
        async_wrapped = cast(
            Callable[[Transition[StateT, TriggerT]], Awaitable[None]], wrapped_action
        )
        return AsyncExitAction(async_wrapped, invocation_info)
    else:
        sync_wrapped = cast(
            Callable[[Transition[StateT, TriggerT]], None], wrapped_action
        )
        return SyncExitAction(sync_wrapped, invocation_info)


def create_activate_action_behavior(
    action_def: ActionDef,
) -> ActivateActionBehaviour[StateT, TriggerT]:
    """Factory to create sync/async activate action behaviors."""
    action, description_override = _get_action_and_description(action_def)
    invocation_info = InvocationInfo.from_callable(action, description_override)
    is_async = invocation_info.is_async

    # Activate actions expect no arguments
    wrapped_action = _build_wrapper(action, [], is_async)

    if is_async:
        async_wrapped = cast(Callable[[], Awaitable[None]], wrapped_action)
        return AsyncActivateAction(async_wrapped, invocation_info)
    else:
        sync_wrapped = cast(Callable[[], None], wrapped_action)
        return SyncActivateAction(sync_wrapped, invocation_info)


def create_deactivate_action_behavior(
    action_def: ActionDef,
) -> DeactivateActionBehaviour[StateT, TriggerT]:
    """Factory to create sync/async deactivate action behaviors."""
    action, description_override = _get_action_and_description(action_def)
    invocation_info = InvocationInfo.from_callable(action, description_override)
    is_async = invocation_info.is_async

    # Deactivate actions expect no arguments
    wrapped_action = _build_wrapper(action, [], is_async)

    if is_async:
        async_wrapped = cast(Callable[[], Awaitable[None]], wrapped_action)
        return AsyncDeactivateAction(async_wrapped, invocation_info)
    else:
        sync_wrapped = cast(Callable[[], None], wrapped_action)
        return SyncDeactivateAction(sync_wrapped, invocation_info)
