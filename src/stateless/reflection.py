from typing import List, Optional, Type, Any, Tuple, Union, Callable
from pydantic import BaseModel, Field
import inspect

# --- Basic Invocation Info ---


class InvocationInfo(BaseModel):
    """Describes a method or function used in the state machine configuration."""

    method_name: Optional[str] = Field(
        None, description="The name of the method/function."
    )
    description: str = Field(
        ...,
        description="A description of the invocation (e.g., method name or provided description).",
    )
    is_async: bool = Field(
        False, description="Whether the method/function is asynchronous."
    )

    @classmethod
    def from_callable(
        cls, func: Callable[..., Any], description: Optional[str] = None
    ) -> "InvocationInfo":
        """Creates InvocationInfo from a callable."""
        method_name = getattr(func, "__name__", None)
        if description is None and method_name and "<lambda>" not in method_name:
            desc = method_name
        elif description is not None:
            desc = description
        else:
            desc = "Function"  # Default for lambdas without description

        return cls(
            method_name=method_name or "<lambda>",
            description=desc,
            is_async=inspect.iscoroutinefunction(func),
        )


# --- Guard Info ---


class GuardInfo(BaseModel):
    """Information about a guard condition."""

    method_description: InvocationInfo = Field(
        ..., description="Details of the guard method."
    )
    # We might not need 'guard' itself here if method_description is sufficient


# --- Action Info ---


class ActionInfo(BaseModel):
    """Information about an action executed on entry, exit, activation, or deactivation."""

    method_description: InvocationInfo = Field(
        ..., description="Details of the action method."
    )
    from_trigger: Optional[Any] = Field(
        None, description="If the action is associated with a specific trigger."
    )


# --- Trigger Info ---


class TriggerInfo(BaseModel):
    """Information about a trigger."""

    underlying_trigger: Any = Field(..., description="The trigger object.")
    # Store parameter types explicitly if set via set_trigger_parameters
    parameter_types: Optional[List[Type]] = Field(
        None, description="Explicitly defined types of parameters the trigger accepts."
    )
    # Store inferred parameter names/types from usage (e.g., action/guard signatures) as fallback/hint
    inferred_parameter_signature: Optional[str] = Field(
        None,
        description="Inferred parameter signature from usage (e.g., '(int, str)').",
    )


# --- Transition Info ---


class TransitionInfo(BaseModel):
    """Information about a permitted transition."""

    trigger: TriggerInfo = Field(
        ..., description="The trigger that causes this transition."
    )
    destination_state: Any = Field(
        ..., description="The state that will be transitioned to."
    )
    guard_conditions: List[GuardInfo] = Field(
        default_factory=list,
        description="Guard conditions that must be met for the transition.",
    )
    # Note: C# includes 'source', but it's implicit in the StateInfo containing this TransitionInfo


# --- Dynamic Transition Info ---
class DynamicStateInfo(BaseModel):
    """Information about a possible destination state of a dynamic transition"""

    destination_state: Any = Field(
        ..., description="The state that will be transitioned to."
    )
    criteria: Any = Field(..., description="The criteria for the transition")


class DynamicStateInfos(BaseModel):
    """Information about possible destination states of a dynamic transition"""

    possible_destinations: List[DynamicStateInfo] = Field(
        default_factory=list, description="Possible destination states"
    )


class DynamicTransitionInfo(BaseModel):
    """Information about a permitted dynamic transition."""

    trigger: TriggerInfo = Field(
        ..., description="The trigger that causes this transition."
    )
    destination_state_selector_description: InvocationInfo = Field(
        ..., description="Details of the dynamic destination selector function."
    )
    guard_conditions: List[GuardInfo] = Field(
        default_factory=list,
        description="Guard conditions that must be met for the transition.",
    )
    possible_destinations: Optional[DynamicStateInfos] = Field(
        None, description="Possible destination states, if known"
    )


# --- Internal Transition Info ---
class InternalTransitionInfo(BaseModel):
    """Information about an internal transition (actions executed, no state change)."""

    trigger: TriggerInfo = Field(
        ..., description="The trigger that causes this internal transition."
    )
    actions: List[ActionInfo] = Field(
        default_factory=list,
        description="Actions executed during the internal transition.",
    )
    guard_conditions: List[GuardInfo] = Field(
        default_factory=list, description="Guard conditions that must be met."
    )


# --- Ignored Trigger Info ---


class IgnoredTransitionInfo(BaseModel):
    """Information about an ignored trigger."""

    trigger: TriggerInfo = Field(..., description="The trigger that is ignored.")
    guard_conditions: List[GuardInfo] = Field(
        default_factory=list,
        description="Guard conditions that must be met for the trigger to be ignored.",
    )


# --- State Info ---


class StateInfo(BaseModel):
    """Information about a single state."""

    underlying_state: Any = Field(..., description="The state object.")
    entry_actions: List[ActionInfo] = Field(
        default_factory=list, description="Actions performed upon entering the state."
    )
    exit_actions: List[ActionInfo] = Field(
        default_factory=list, description="Actions performed upon exiting the state."
    )
    activate_actions: List[ActionInfo] = Field(
        default_factory=list, description="Actions performed when activating the state."
    )
    deactivate_actions: List[ActionInfo] = Field(
        default_factory=list,
        description="Actions performed when deactivating the state.",
    )
    substates: List["StateInfo"] = Field(
        default_factory=list, description="Nested substates."
    )
    # Use Any for superstate_value to avoid type issues with different state types (Enum, str, etc.)
    superstate_value: Optional[Any] = Field(
        None, description="The value of the parent state, if this is a substate."
    )
    fixed_transitions: List[TransitionInfo] = Field(
        default_factory=list, description="Transitions permitted from this state."
    )
    internal_transitions: List[InternalTransitionInfo] = Field(
        default_factory=list, description="Internal transitions handled in this state."
    )
    ignored_triggers: List[IgnoredTransitionInfo] = Field(
        default_factory=list, description="Triggers ignored in this state."
    )
    dynamic_transitions: List[DynamicTransitionInfo] = Field(
        default_factory=list,
        description="Dynamic transitions permitted from this state.",
    )
    initial_transition_target: Optional[Any] = Field(
        None,
        description="The target state for the initial transition into this superstate.",
    )

    model_config = {
        "arbitrary_types_allowed": True,
    }


# --- State Machine Info ---


class StateMachineInfo(BaseModel):
    """Provides information about the structure of a state machine."""

    states: List[StateInfo] = Field(
        ..., description="All states configured in the machine."
    )
    state_type: Type = Field(..., description="The type of the state objects.")
    trigger_type: Type = Field(..., description="The type of the trigger objects.")
    initial_state: Any = Field(..., description="The initial state of the machine.")

    model_config = {
        "arbitrary_types_allowed": True,
    }


# Helper type for callables used in configuration
GuardDef = Tuple[Callable[..., bool], Optional[str]]
ActionDef = Union[
    Callable, Tuple[Callable, Optional[str]]
]  # Action or (Action, Description)
