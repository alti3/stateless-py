"""
Provides the fluent API for configuring states (Permit, Ignore, OnEntry, etc.).
"""

# Placeholder - Core implementation to follow
from typing import (
    Generic,
    Callable,
    Sequence,
    Optional,
    Union,
    overload,
)

from .transition import StateT, TriggerT
from .state_representation import StateRepresentation
from .guards import GuardDef, guards_from_definitions
from .actions import (
    ActionDef,
    create_entry_action_behavior,
    create_exit_action_behavior,
    create_activate_action_behavior,
    create_deactivate_action_behavior,
    ActionFuncResult,
)
from .trigger_behaviour import (
    TransitioningTriggerBehaviour,
    IgnoredTriggerBehaviour,
    ReentryTriggerBehaviour,
    InternalTriggerBehaviour,
    DynamicTriggerBehaviour,
    DestinationStateSelector,
)
from .exceptions import ConfigurationError

# Forward declaration for StateMachine type hint
if False:  # TYPE_CHECKING
    from .state_machine import StateMachine


# --- Helper Function ---
def _get_action_and_description(
    action_def: ActionDef,
) -> tuple[Callable[..., ActionFuncResult], Optional[str]]:
    """Extracts the callable action and its description from ActionDef."""
    if callable(action_def):
        return action_def, None
    elif (
        isinstance(action_def, tuple)
        and len(action_def) == 2
        and callable(action_def[0])
    ):
        # Type checker might need help here depending on ActionDef definition
        return action_def[0], action_def[1]  # type: ignore
    else:
        # This case should ideally be prevented by type hinting ActionDef correctly,
        # but adding a runtime check for robustness.
        raise TypeError(
            f"Invalid ActionDef format: {action_def!r}. Expected callable or (callable, str)."
        )


class StateConfiguration(Generic[StateT, TriggerT]):
    """Fluent configuration for a single state."""

    def __init__(
        self,
        machine: "StateMachine[StateT, TriggerT]",  # Use string literal for forward ref
        representation: StateRepresentation[StateT, TriggerT],
        lookup_func: Callable[[StateT], StateRepresentation[StateT, TriggerT]],
    ):
        self._machine = machine
        self._representation = representation
        self._lookup_func = lookup_func

    @property
    def state(self) -> StateT:
        """The state being configured."""
        return self._representation.state

    def _validate_trigger_type(self, trigger: TriggerT) -> None:
        """Checks if the trigger type matches the machine's trigger type, if known."""
        # TODO: Implement type checking logic if machine._trigger_type is set

        # Placeholder: Basic check if trigger is hashable (required for dict keys)
        try:
            hash(trigger)
        except TypeError:
            raise ConfigurationError(
                f"Triggers must be hashable. Got trigger: {trigger!r}"
            )

    # --- Permit ---
    @overload
    def permit(
        self,
        trigger: TriggerT,
        destination_state: StateT,
        guard: Union[Callable[..., bool], Sequence[GuardDef]] = (),
        guard_description: Optional[str] = None,
    ) -> "StateConfiguration[StateT, TriggerT]": ...

    @overload
    def permit(
        self,
        trigger: TriggerT,
        destination_state: StateT,
        *,
        guards: Sequence[GuardDef] = (),
    ) -> "StateConfiguration[StateT, TriggerT]": ...

    def permit(
        self,
        trigger: TriggerT,
        destination_state: StateT,
        guard: Union[Callable[..., bool], Sequence[GuardDef]] = (),
        guard_description: Optional[str] = None,
        *,
        guards: Optional[Sequence[GuardDef]] = None,  # Keyword-only alternative
    ) -> "StateConfiguration[StateT, TriggerT]":
        """
        Accept the specified trigger and transition to the destination state.

        Args:
            trigger: The trigger to accept.
            destination_state: The state to transition to.
            guard: A single guard function (callable) or a sequence of (guard_func, description) tuples.
            guard_description: Description for the single guard function (if guard is a callable).
            guards: Alternative keyword-only argument for a sequence of (guard_func, description) tuples.

        Returns:
            The current StateConfiguration instance for fluent chaining.
        """
        self._validate_trigger_type(trigger)
        guard_defs: Sequence[GuardDef]

        if guards is not None:
            if callable(guard) or guard_description is not None:
                raise ConfigurationError(
                    "Cannot specify both 'guard'/'guard_description' and 'guards' keyword argument."
                )
            guard_defs = guards
        elif callable(guard):
            guard_defs = [(guard, guard_description)]
        elif isinstance(guard, Sequence):
            guard_defs = guard  # Assumes it's already Sequence[GuardDef]
        else:
            raise TypeError(
                "`guard` must be a callable or a sequence of (callable, description) tuples."
            )

        transition_guard = guards_from_definitions(guard_defs)
        behaviour = TransitioningTriggerBehaviour(
            trigger, destination_state, transition_guard
        )
        self._representation.add_trigger_behaviour(behaviour)
        return self

    # --- PermitIf --- (Convenience, maps to permit with guards)
    def permit_if(
        self,
        trigger: TriggerT,
        destination_state: StateT,
        guard: Callable[..., bool],
        guard_description: Optional[str] = None,
    ) -> "StateConfiguration[StateT, TriggerT]":
        """
        Accept the specified trigger and transition to the destination state if the guard function returns True.
        Syntactic sugar for permit(trigger, destination_state, guard=...).
        """
        return self.permit(
            trigger, destination_state, guard=guard, guard_description=guard_description
        )

    # --- PermitReentry ---
    # ... (similar overloads/implementation as permit, using ReentryTriggerBehaviour) ...
    def permit_reentry(
        self,
        trigger: TriggerT,
        guard: Union[Callable[..., bool], Sequence[GuardDef]] = (),
        guard_description: Optional[str] = None,
        *,
        guards: Optional[Sequence[GuardDef]] = None,
    ) -> "StateConfiguration[StateT, TriggerT]":
        """Accept the specified trigger and perform reentry actions (exit/entry) for the current state."""
        self._validate_trigger_type(trigger)
        guard_defs: Sequence[GuardDef]
        if guards is not None:
            if callable(guard) or guard_description is not None:
                raise ConfigurationError(
                    "Cannot use both 'guard'/'guard_description' and 'guards'."
                )
            guard_defs = guards
        elif callable(guard):
            guard_defs = [(guard, guard_description)]
        elif isinstance(guard, Sequence):
            guard_defs = guard
        else:
            raise TypeError("`guard` must be callable or sequence.")

        transition_guard = guards_from_definitions(guard_defs)
        # Destination for reentry is the state itself
        behaviour = ReentryTriggerBehaviour(trigger, transition_guard, self.state)
        self._representation.add_trigger_behaviour(behaviour)
        return self

    # --- PermitReentryIf ---
    def permit_reentry_if(
        self,
        trigger: TriggerT,
        guard: Callable[..., bool],
        guard_description: Optional[str] = None,
    ) -> "StateConfiguration[StateT, TriggerT]":
        """Accept the specified trigger and perform reentry actions if the guard function returns True."""
        return self.permit_reentry(
            trigger, guard=guard, guard_description=guard_description
        )

    # --- Ignore ---
    # ... (similar overloads/implementation as permit, using IgnoredTriggerBehaviour) ...
    def ignore(
        self,
        trigger: TriggerT,
        guard: Union[Callable[..., bool], Sequence[GuardDef]] = (),
        guard_description: Optional[str] = None,
        *,
        guards: Optional[Sequence[GuardDef]] = None,
    ) -> "StateConfiguration[StateT, TriggerT]":
        """Ignore the specified trigger when in this state."""
        self._validate_trigger_type(trigger)
        guard_defs: Sequence[GuardDef]
        if guards is not None:
            if callable(guard) or guard_description is not None:
                raise ConfigurationError(
                    "Cannot use both 'guard'/'guard_description' and 'guards'."
                )
            guard_defs = guards
        elif callable(guard):
            guard_defs = [(guard, guard_description)]
        elif isinstance(guard, Sequence):
            guard_defs = guard
        else:
            raise TypeError("`guard` must be callable or sequence.")

        transition_guard = guards_from_definitions(guard_defs)
        behaviour = IgnoredTriggerBehaviour(trigger, transition_guard)
        self._representation.add_trigger_behaviour(behaviour)
        return self

    # --- IgnoreIf ---
    def ignore_if(
        self,
        trigger: TriggerT,
        guard: Callable[..., bool],
        guard_description: Optional[str] = None,
    ) -> "StateConfiguration[StateT, TriggerT]":
        """Ignore the specified trigger when in this state if the guard function returns True."""
        return self.ignore(trigger, guard=guard, guard_description=guard_description)

    # --- OnEntry ---
    def on_entry(
        self,
        entry_action: ActionDef,
        description: Optional[
            str
        ] = None,  # Allow overriding description even if tuple used
    ) -> "StateConfiguration[StateT, TriggerT]":
        """Specify an action to be executed when entering this state."""
        action_callable, desc_from_tuple = _get_action_and_description(entry_action)
        final_description = (
            description or desc_from_tuple
        )  # Explicit description takes precedence
        action_def_final: ActionDef = (
            (action_callable, final_description)
            if final_description
            else action_callable
        )

        behaviour = create_entry_action_behavior(action_def_final)
        self._representation.add_entry_action(behaviour)
        return self

    # --- OnEntryFrom ---
    def on_entry_from(
        self,
        trigger: TriggerT,
        entry_action: ActionDef,
        description: Optional[str] = None,
    ) -> "StateConfiguration[StateT, TriggerT]":
        """Specify an action to be executed when entering this state via the specified trigger."""
        self._validate_trigger_type(trigger)
        action_callable, desc_from_tuple = _get_action_and_description(entry_action)
        final_description = description or desc_from_tuple
        action_def_final: ActionDef = (
            (action_callable, final_description)
            if final_description
            else action_callable
        )

        # Pass the trigger to the factory
        behaviour = create_entry_action_behavior(action_def_final, trigger=trigger)
        self._representation.add_entry_action(behaviour)
        return self

    # --- OnExit ---
    def on_exit(
        self, exit_action: ActionDef, description: Optional[str] = None
    ) -> "StateConfiguration[StateT, TriggerT]":
        """Specify an action to be executed when exiting this state."""
        action_callable, desc_from_tuple = _get_action_and_description(exit_action)
        final_description = description or desc_from_tuple
        action_def_final: ActionDef = (
            (action_callable, final_description)
            if final_description
            else action_callable
        )

        behaviour = create_exit_action_behavior(action_def_final)
        self._representation.add_exit_action(behaviour)
        return self

    # --- OnActivate ---
    def on_activate(
        self, activate_action: ActionDef, description: Optional[str] = None
    ) -> "StateConfiguration[StateT, TriggerT]":
        """Specify an action to be executed when activating this state (entering state or initial state)."""
        action_callable, desc_from_tuple = _get_action_and_description(activate_action)
        final_description = description or desc_from_tuple
        action_def_final: ActionDef = (
            (action_callable, final_description)
            if final_description
            else action_callable
        )

        behaviour = create_activate_action_behavior(action_def_final)
        self._representation.add_activate_action(behaviour)
        return self

    # --- OnDeactivate ---
    def on_deactivate(
        self, deactivate_action: ActionDef, description: Optional[str] = None
    ) -> "StateConfiguration[StateT, TriggerT]":
        """Specify an action to be executed when deactivating this state (exiting state)."""
        action_callable, desc_from_tuple = _get_action_and_description(
            deactivate_action
        )
        final_description = description or desc_from_tuple
        action_def_final: ActionDef = (
            (action_callable, final_description)
            if final_description
            else action_callable
        )

        behaviour = create_deactivate_action_behavior(action_def_final)
        self._representation.add_deactivate_action(behaviour)
        return self

    # --- SubstateOf ---
    def substate_of(self, superstate: StateT) -> "StateConfiguration[StateT, TriggerT]":
        """Declare this state as a substate of the specified superstate."""
        super_rep = self._lookup_func(superstate)
        self._representation.superstate = super_rep
        super_rep.add_substate(self._representation)
        return self

    # --- InternalTransition ---
    @overload
    def internal_transition(
        self,
        trigger: TriggerT,
        action: Callable[..., ActionFuncResult],
        guard: Union[Callable[..., bool], Sequence[GuardDef]] = (),
        guard_description: Optional[str] = None,
        action_description: Optional[str] = None,
    ) -> "StateConfiguration[StateT, TriggerT]": ...

    @overload
    def internal_transition(
        self,
        trigger: TriggerT,
        action: Callable[..., ActionFuncResult],
        *,
        guards: Sequence[GuardDef] = (),
        action_description: Optional[str] = None,
    ) -> "StateConfiguration[StateT, TriggerT]": ...

    def internal_transition(
        self,
        trigger: TriggerT,
        action: Callable[..., ActionFuncResult],
        guard: Union[Callable[..., bool], Sequence[GuardDef]] = (),
        guard_description: Optional[str] = None,
        action_description: Optional[str] = None,
        *,
        guards: Optional[Sequence[GuardDef]] = None,
    ) -> "StateConfiguration[StateT, TriggerT]":
        """
        Accept the specified trigger, execute the action, but do not transition state.
        Exit/Entry actions are not executed.

        Args:
            trigger: The trigger to accept.
            action: The action function to execute. It can accept the `Transition` object
                    and any parameters passed during `fire`.
            guard: A single guard function or sequence of (guard, description) tuples.
            guard_description: Description for the single guard function.
            action_description: Optional description for the action function.
            guards: Alternative keyword-only argument for guards.

        Returns:
            The current StateConfiguration instance.
        """
        self._validate_trigger_type(trigger)
        guard_defs: Sequence[GuardDef]

        if guards is not None:
            if callable(guard) or guard_description is not None:
                raise ConfigurationError(
                    "Cannot specify both 'guard'/'guard_description' and 'guards' keyword argument."
                )
            guard_defs = guards
        elif callable(guard):
            guard_defs = [(guard, guard_description)]
        elif isinstance(guard, Sequence):
            guard_defs = guard
        else:
            raise TypeError(
                "`guard` must be a callable or a sequence of (callable, description) tuples."
            )

        transition_guard = guards_from_definitions(guard_defs)
        # TODO: Wrap the action properly similar to how entry/exit actions are wrapped
        # For now, pass the raw action; InternalTriggerBehaviour needs refinement
        behaviour = InternalTriggerBehaviour(
            trigger, transition_guard, action, action_description
        )
        self._representation.add_trigger_behaviour(behaviour)
        return self

    # --- Dynamic ---
    @overload
    def dynamic(
        self,
        trigger: TriggerT,
        destination_selector: DestinationStateSelector,
        guard: Union[Callable[..., bool], Sequence[GuardDef]] = (),
        guard_description: Optional[str] = None,
        selector_description: Optional[str] = None,
    ) -> "StateConfiguration[StateT, TriggerT]": ...

    @overload
    def dynamic(
        self,
        trigger: TriggerT,
        destination_selector: DestinationStateSelector,
        *,
        guards: Sequence[GuardDef] = (),
        selector_description: Optional[str] = None,
    ) -> "StateConfiguration[StateT, TriggerT]": ...

    def dynamic(
        self,
        trigger: TriggerT,
        destination_selector: DestinationStateSelector,
        guard: Union[Callable[..., bool], Sequence[GuardDef]] = (),
        guard_description: Optional[str] = None,
        selector_description: Optional[str] = None,
        *,
        guards: Optional[Sequence[GuardDef]] = None,
    ) -> "StateConfiguration[StateT, TriggerT]":
        """
        Accept the specified trigger and transition to a state determined dynamically by the destination_selector function.

        Args:
            trigger: The trigger to accept.
            destination_selector: A function that returns the destination state.
                                  It can accept parameters passed during `fire`.
            guard: A single guard function or sequence of (guard, description) tuples.
            guard_description: Description for the single guard function.
            selector_description: Optional description for the selector function.
            guards: Alternative keyword-only argument for guards.

        Returns:
            The current StateConfiguration instance.
        """
        self._validate_trigger_type(trigger)
        guard_defs: Sequence[GuardDef]

        if guards is not None:
            if callable(guard) or guard_description is not None:
                raise ConfigurationError(
                    "Cannot specify both 'guard'/'guard_description' and 'guards' keyword argument."
                )
            guard_defs = guards
        elif callable(guard):
            guard_defs = [(guard, guard_description)]
        elif isinstance(guard, Sequence):
            guard_defs = guard
        else:
            raise TypeError(
                "`guard` must be a callable or a sequence of (callable, description) tuples."
            )

        transition_guard = guards_from_definitions(guard_defs)
        behaviour = DynamicTriggerBehaviour(
            trigger, destination_selector, transition_guard, selector_description
        )
        self._representation.add_trigger_behaviour(behaviour)
        return self

    # --- InitialTransition ---
    def initial_transition(
        self, target_state: StateT
    ) -> "StateConfiguration[StateT, TriggerT]":
        """
        Specifies the target state for the initial transition into this superstate.
        This state must be configured as a superstate (or have substates).
        """
        # Ensure target is actually a substate (or sub-substate, etc.)? C# doesn't seem to enforce this strictly at config time.
        target_rep = self._lookup_func(
            target_state
        )  # Ensure target state exists in config
        if not target_rep.is_included_in(self.state):
            raise ConfigurationError(
                f"Initial transition target state {target_state!r} must be a substate of {self.state!r}."
            )

        self._representation.initial_transition_target = target_state
        return self

    # --- Trigger Parameters ---
    # TODO: Add methods for configuring parameterized triggers if needed (e.g., `trigger_with_parameters`)

    def __repr__(self) -> str:
        return f"StateConfiguration(state={self.state!r})"
