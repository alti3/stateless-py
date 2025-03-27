"""
Helpers for creating and managing parameterized triggers.
"""

# Placeholder - Implementation might involve creating wrapper classes or using type hints effectively
from typing import (
    TypeVar,
    Generic,
    Type,
    Tuple,
    Sequence,
    Any,
    Callable,
    Optional,
    List,
)

StateT = TypeVar("StateT")
TriggerT = TypeVar("TriggerT")
T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")

# Option 1: Define classes for parameterized triggers (similar to C#)


class TriggerWithParameters1(Generic[T1, TriggerT]):
    """Represents a trigger that requires one parameter."""

    def __init__(self, underlying_trigger: TriggerT, arg_type: Type[T1]):
        self._trigger = underlying_trigger
        self._arg_type = arg_type
        # TODO: Store type info for validation/reflection

    @property
    def trigger(self) -> TriggerT:
        return self._trigger

    # How to use this? StateMachine.fire might need modification
    # or users pass (trigger_obj, param1)


class TriggerWithParameters2(Generic[T1, T2, TriggerT]):
    """Represents a trigger that requires two parameters."""

    # ... similar implementation ...
    pass


class TriggerWithParameters3(Generic[T1, T2, T3, TriggerT]):
    """Represents a trigger that requires three parameters."""

    # ... similar implementation ...
    pass


# Option 2: Rely on type hints and runtime checks within StateMachine/StateConfiguration

# Example: In StateConfiguration.permit, inspect guard/action signatures
#          to infer expected parameter types for the trigger.

# Example: StateMachine.fire could validate passed *args against expected types
#          stored during configuration.

# This might be simpler and more Pythonic, avoiding extra classes.
# Let's assume Option 2 for now and build validation into the core logic.


# Helper function to potentially create TriggerInfo with parameter types
def get_parameter_types(func: Callable) -> Optional[List[Tuple[str, Type]]]:
    """Inspects a function (guard/action) to guess trigger parameter types."""
    # This is complex and potentially unreliable.
    # It depends on how parameters are passed (e.g., after Transition object).
    # Placeholder - needs careful design based on how actions/guards receive trigger args.
    return None
