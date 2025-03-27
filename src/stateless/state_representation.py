"""
Internal representation of a state and its associated behaviours (transitions, actions).
"""

# Placeholder - Core implementation to follow
from typing import (
    TypeVar,
    Generic,
    Optional,
    List,
    Dict,
    Callable,
    Sequence,
    Any,
    Tuple,
    Awaitable,
)

from .transition import StateT, TriggerT, Transition, InitialTransition
from .trigger_behaviour import TriggerBehaviour, TriggerBehaviourResult
from .actions import (
    EntryActionBehaviour,
    ExitActionBehaviour,
    ActivateActionBehaviour,
    DeactivateActionBehaviour,
)

Args = Sequence[Any]


class StateRepresentation(Generic[StateT, TriggerT]):
    """Holds configuration information for a single state."""

    def __init__(self, state: StateT):
        self._state = state
        self._trigger_behaviours: Dict[
            TriggerT, List[TriggerBehaviour[StateT, TriggerT]]
        ] = {}
        self._entry_actions: List[EntryActionBehaviour[StateT, TriggerT]] = []
        self._exit_actions: List[ExitActionBehaviour[StateT, TriggerT]] = []
        self._activate_actions: List[ActivateActionBehaviour[StateT, TriggerT]] = []
        self._deactivate_actions: List[DeactivateActionBehaviour[StateT, TriggerT]] = []
        self._substates: List["StateRepresentation[StateT, TriggerT]"] = []
        self._superstate: Optional["StateRepresentation[StateT, TriggerT]"] = None
        self._initial_transition_target: Optional[StateT] = (
            None  # For initial transition into this superstate
        )

    @property
    def state(self) -> StateT:
        return self._state

    @property
    def substates(self) -> List["StateRepresentation[StateT, TriggerT]"]:
        return self._substates

    @property
    def superstate(self) -> Optional["StateRepresentation[StateT, TriggerT]"]:
        return self._superstate

    @superstate.setter
    def superstate(
        self, value: Optional["StateRepresentation[StateT, TriggerT]"]
    ) -> None:
        self._superstate = value

    @property
    def entry_actions(self) -> List[EntryActionBehaviour[StateT, TriggerT]]:
        return self._entry_actions

    @property
    def exit_actions(self) -> List[ExitActionBehaviour[StateT, TriggerT]]:
        return self._exit_actions

    @property
    def activate_actions(self) -> List[ActivateActionBehaviour[StateT, TriggerT]]:
        return self._activate_actions

    @property
    def deactivate_actions(self) -> List[DeactivateActionBehaviour[StateT, TriggerT]]:
        return self._deactivate_actions

    @property
    def trigger_behaviours(
        self,
    ) -> Dict[TriggerT, List[TriggerBehaviour[StateT, TriggerT]]]:
        return self._trigger_behaviours

    @property
    def initial_transition_target(self) -> Optional[StateT]:
        return self._initial_transition_target

    @initial_transition_target.setter
    def initial_transition_target(self, value: Optional[StateT]) -> None:
        self._initial_transition_target = value

    def add_trigger_behaviour(
        self, behaviour: TriggerBehaviour[StateT, TriggerT]
    ) -> None:
        """Adds a new trigger behaviour for this state."""
        trigger = behaviour.trigger
        if trigger not in self._trigger_behaviours:
            self._trigger_behaviours[trigger] = []
        self._trigger_behaviours[trigger].append(behaviour)

    def add_entry_action(self, action: EntryActionBehaviour[StateT, TriggerT]) -> None:
        self._entry_actions.append(action)

    def add_exit_action(self, action: ExitActionBehaviour[StateT, TriggerT]) -> None:
        self._exit_actions.append(action)

    def add_activate_action(
        self, action: ActivateActionBehaviour[StateT, TriggerT]
    ) -> None:
        self._activate_actions.append(action)

    def add_deactivate_action(
        self, action: DeactivateActionBehaviour[StateT, TriggerT]
    ) -> None:
        self._deactivate_actions.append(action)

    def add_substate(self, substate: "StateRepresentation[StateT, TriggerT]") -> None:
        """Adds a substate to this state."""
        if substate not in self._substates:
            self._substates.append(substate)

    def includes(self, state: StateT) -> bool:
        """Checks if the given state is this state or a substate."""
        if self._state == state:
            return True
        return any(s.includes(state) for s in self._substates)

    def is_included_in(self, state: StateT) -> bool:
        """Checks if this state is equal to or a substate of the given state."""
        if self._state == state:
            return True
        if self._superstate:
            return self._superstate.is_included_in(state)
        return False

    async def find_handler_for_trigger(
        self, trigger: TriggerT, args: Args
    ) -> TriggerBehaviourResult[StateT, TriggerT]:
        """
        Finds a handler for the trigger in this state or its superstates.
        Returns the handler and any unmet guard descriptions.
        """
        result = await self._find_local_handler(trigger, args)
        if result.handler is not None:
            return result  # Found a handler (guards may or may not be met)

        # If no local handler found (or guards unmet for all local handlers), check superstate
        if self.superstate:
            # Pass through the unmet guards from the local search if any existed
            super_result = await self.superstate.find_handler_for_trigger(trigger, args)
            # If superstate found a handler OR if local search had unmet guards, return that result
            if super_result.handler or result.unmet_guard_conditions:
                # Prioritize superstate handler if found, otherwise keep local unmet guards
                if super_result.handler:
                    return super_result
                else:
                    # Combine unmet guards? C# seems to only return unmet guards for the *first* level where a handler was found but guards failed.
                    # Let's stick to that: return the local unmet guards if superstate had no handler at all.
                    return result
            else:
                # Neither local nor superstate had a handler or unmet guards for this trigger
                return TriggerBehaviourResult(None, [])
        else:
            # No local handler, no superstate, return the result from local search (which has no handler)
            return result

    async def _find_local_handler(
        self, trigger: TriggerT, args: Args
    ) -> TriggerBehaviourResult[StateT, TriggerT]:
        """Finds a handler for the trigger specifically within this state."""
        possible: List[TriggerBehaviour[StateT, TriggerT]] = (
            self._trigger_behaviours.get(trigger, [])
        )
        unmet_guards: List[str] = []

        for behaviour in possible:
            guards_met = await behaviour.guard.conditions_met_async(args)
            if guards_met:
                # Found a behaviour whose guards are met
                return TriggerBehaviourResult(behaviour, [])
            else:
                # Guards not met, collect descriptions
                unmet = await behaviour.guard.unmet_conditions_async(args)
                unmet_guards.extend(unmet)

        # No behaviour found with met guards, return collected unmet guard descriptions
        # If 'possible' was empty, unmet_guards will also be empty.
        return TriggerBehaviourResult(None, unmet_guards)

    async def enter(
        self, transition: Transition[StateT, TriggerT], entry_args: Args
    ) -> None:
        """Executes entry actions for this state and triggers initial transitions if applicable."""
        is_initial = isinstance(transition, InitialTransition)

        if transition.is_reentry:
            await self._execute_entry_actions_async(transition, entry_args)
            await self._execute_activate_actions_async()  # Re-activate on reentry
        elif is_initial or not self.is_included_in(transition.source):
            # Entering from outside or via initial transition
            if self.superstate:
                # Ensure superstate is entered first (recursive call)
                await self.superstate.enter(transition, entry_args)

            # Execute this state's entry actions
            await self._execute_entry_actions_async(transition, entry_args)
            # Activate this state
            await self._execute_activate_actions_async()

            # Handle initial transition *after* entering and activating this superstate
            if self.initial_transition_target is not None:
                # Find the representation of the target substate
                target_rep = self._find_substate_representation(
                    self.initial_transition_target
                )
                if target_rep:
                    # Create an InitialTransition object for the substate entry
                    initial_sub_transition = InitialTransition(
                        self.state,  # Source is the superstate
                        target_rep.state,  # Destination is the target substate
                        transition.trigger,  # Propagate original trigger? Or None? Let's use original.
                        entry_args,  # Propagate args?
                    )
                    # Recursively call enter on the target substate
                    await target_rep.enter(initial_sub_transition, entry_args)
                else:
                    # This indicates a configuration error if target not found
                    from .exceptions import ConfigurationError  # Local import

                    raise ConfigurationError(
                        f"Initial transition target '{self.initial_transition_target}' not found as substate of '{self.state}'."
                    )

    async def exit(self, transition: Transition[StateT, TriggerT]) -> None:
        """Executes exit actions for this state."""
        if transition.is_reentry:
            await self._execute_deactivate_actions_async()  # Deactivate on reentry exit
            await self._execute_exit_actions_async(transition)
        elif not self.is_included_in(transition.destination):
            # Exiting to outside this state's hierarchy
            await self._execute_deactivate_actions_async()  # Deactivate before exit
            await self._execute_exit_actions_async(transition)
            if self.superstate:
                # Ensure superstate is exited last (recursive call)
                await self.superstate.exit(transition)

    def _find_substate_representation(
        self, state: StateT
    ) -> Optional["StateRepresentation[StateT, TriggerT]"]:
        """Finds a direct or indirect substate representation by state value."""
        if self.state == state:  # Should not happen for initial target, but check
            return self
        for sub in self.substates:
            found = sub._find_substate_representation(state)
            if found:
                return found
        return None

    async def activate(self) -> None:
        """Executes activate actions for this state and potentially substates."""
        # TODO: Implement proper activation cascade if needed
        await self._execute_activate_actions_async()

    async def deactivate(self) -> None:
        """Executes deactivate actions for this state and potentially substates."""
        # TODO: Implement proper deactivation cascade if needed
        await self._execute_deactivate_actions_async()

    # --- Internal Action Execution ---
    async def _execute_entry_actions_async(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> None:
        for action in self.entry_actions:
            await action.execute_async(transition, args)

    async def _execute_exit_actions_async(
        self, transition: Transition[StateT, TriggerT]
    ) -> None:
        for action in self.exit_actions:
            await action.execute_async(transition)

    async def _execute_activate_actions_async(self) -> None:
        for action in self.activate_actions:
            await action.execute_async()

    async def _execute_deactivate_actions_async(self) -> None:
        for action in self.deactivate_actions:
            await action.execute_async()

    def __repr__(self) -> str:
        return f"StateRepresentation({self._state!r})"

    def __hash__(self) -> int:
        # Assumes state is hashable
        return hash(self._state)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, StateRepresentation):
            return self._state == other._state
        return False
