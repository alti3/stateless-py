from typing import TypeVar, Generic, Sequence, Any, Optional, Callable

StateT = TypeVar("StateT")
TriggerT = TypeVar("TriggerT")


class Transition(Generic[StateT, TriggerT]):
    """Represents a transition between states."""

    def __init__(
        self,
        source: StateT,
        destination: StateT,
        trigger: TriggerT,
        parameters: Sequence[Any] = (),
    ):
        self._source = source
        self._destination = destination
        self._trigger = trigger
        self._parameters = tuple(parameters)  # Ensure immutability

    @property
    def source(self) -> StateT:
        """The state transitioned from."""
        return self._source

    @property
    def destination(self) -> StateT:
        """The state transitioned to."""
        return self._destination

    @property
    def trigger(self) -> TriggerT:
        """The trigger that caused the transition."""
        return self._trigger

    @property
    def parameters(self) -> Sequence[Any]:
        """The parameters provided when the trigger was fired."""
        return self._parameters

    @property
    def is_reentry(self) -> bool:
        """True if the transition is a re-entry to the same state (source == destination)."""
        # Assumes states support equality check (e.g., Enums, hashable objects)
        return self.source == self.destination

    def __repr__(self) -> str:
        params_str = f", parameters={self.parameters}" if self.parameters else ""
        return f"Transition(source={self.source!r}, destination={self.destination!r}, trigger={self.trigger!r}{params_str})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transition):
            return NotImplemented
        return (
            self.source == other.source
            and self.destination == other.destination
            and self.trigger == other.trigger
            and self.parameters == other.parameters
        )

    def __hash__(self) -> int:
        # Assumes source, destination, trigger are hashable
        return hash((self.source, self.destination, self.trigger, self.parameters))


class InitialTransition(Transition[StateT, TriggerT]):
    """
    Represents the initial transition into a state.

    Conceptually, for an initial transition into substate `B` of superstate `A`,
    the user configures it based on `A`, but the transition object itself
    represents the move *from* `A` *to* `B`.
    """

    def __init__(
        self,
        source: StateT,
        destination: StateT,
        trigger: TriggerT,
        parameters: Sequence[Any] = (),
    ):
        super().__init__(source, destination, trigger, parameters)

    def __repr__(self) -> str:
        params_str = f", parameters={self.parameters}" if self.parameters else ""
        return f"InitialTransition(source={self.source!r}, destination={self.destination!r}, trigger={self.trigger!r}{params_str})"


# Type alias for the optional handler called when no transition is found for a trigger.
UnmetTriggerHandler = Optional[Callable[[StateT, TriggerT, Sequence[Any]], None]]
UnmetTriggerHandlerAsync = Optional[
    Callable[[StateT, TriggerT, Sequence[Any]], Any]
]  # Can be sync or async
