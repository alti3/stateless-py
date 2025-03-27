from enum import Enum, auto
from typing import Optional, Tuple

from stateless import StateMachine, Transition, InvalidTransitionError


# --- States ---
class State(Enum):
    OPEN = auto()
    ASSIGNED = auto()
    DEFERRED = auto()
    CLOSED = auto()


# --- Triggers ---
class Trigger(Enum):
    ASSIGN = auto()
    DEFER = auto()
    CLOSE = auto()


# --- Bug Class ---
class Bug:
    def __init__(self, title: str, initial_state: State = State.OPEN):
        self.title = title
        self._assignee: Optional[str] = None
        self._state = initial_state
        self.state_machine = self._create_state_machine(initial_state)

    def _create_state_machine(
        self, initial_state: State
    ) -> StateMachine[State, Trigger]:
        sm = StateMachine[State, Trigger](
            initial_state,
            state_accessor=lambda: self._state,
            state_mutator=lambda s: self._set_state(s),
        )

        # Configure states and transitions
        sm.configure(State.OPEN).permit(Trigger.ASSIGN, State.ASSIGNED)

        sm.configure(State.ASSIGNED).substate_of(State.OPEN).on_entry_from(
            Trigger.ASSIGN, self._assign
        ).permit(Trigger.CLOSE, State.CLOSED).permit(
            Trigger.DEFER, State.DEFERRED
        ).permit_reentry(Trigger.ASSIGN)  # Allow re-assignment

        sm.configure(State.DEFERRED).substate_of(State.OPEN).on_entry(
            lambda t: self._set_assignee(None)
        ).permit(Trigger.ASSIGN, State.ASSIGNED)

        sm.configure(State.CLOSED).on_entry(
            lambda t: print(f"Bug '{self.title}' Closed.")
        )

        # Set trigger parameters (for demonstration, though not strictly needed for guards/actions here)
        sm.set_trigger_parameters(Trigger.ASSIGN, str)  # Expects assignee name

        return sm

    def _set_state(self, new_state: State):
        print(f"Bug '{self.title}': State changing from {self._state} to {new_state}")
        self._state = new_state

    @property
    def state(self) -> State:
        return self.state_machine.state  # Access via machine

    @property
    def assignee(self) -> Optional[str]:
        return self._assignee

    def _set_assignee(self, assignee: Optional[str]):
        self._assignee = assignee
        print(f"Bug '{self.title}': Assignee set to {assignee or 'None'}")

    # Action for Assign trigger
    def _assign(self, transition: Transition[State, Trigger], args: Tuple[str]):
        assignee = args[0] if args else None
        if assignee:
            self._set_assignee(assignee)
        else:
            # This shouldn't happen if fire is called correctly, but handle defensively
            print("Warning: ASSIGN trigger fired without assignee argument.")
            self._set_assignee(None)

    # Public methods to fire triggers
    def close(self):
        print(f"\nAttempting to Close '{self.title}'...")
        self.state_machine.fire(Trigger.CLOSE)

    def assign(self, assignee: str):
        print(f"\nAttempting to Assign '{self.title}' to {assignee}...")
        if not assignee:
            print("Cannot assign without an assignee name.")
            return
        self.state_machine.fire(Trigger.ASSIGN, assignee)

    def defer(self):
        print(f"\nAttempting to Defer '{self.title}'...")
        self.state_machine.fire(Trigger.DEFER)

    def __str__(self) -> str:
        return f"Bug '{self.title}' [State: {self.state}, Assignee: {self.assignee or 'None'}]"


# --- Usage ---
bug = Bug("Intermittent Failure")
print(bug)

bug.assign("Alice")
print(bug)

bug.defer()
print(bug)

bug.assign("Bob")
print(bug)

bug.close()
print(bug)

# Try assigning a closed bug (should fail)
try:
    bug.assign("Charlie")
except InvalidTransitionError as e:
    print(f"\nError assigning closed bug: {e}")
print(bug)

# --- Introspection ---
print("\n--- Bug Tracker State Machine Info ---")
info = bug.state_machine.get_info()
print(f"Initial State: {info.initial_state}")
for state_info in info.states:
    print(f"\nState: {state_info.underlying_state}")
    if state_info.superstate_value:
        print(f"  Substate of: {state_info.superstate_value}")
    if state_info.entry_actions:
        print(
            f"  Entry Actions: {[a.method_description.description for a in state_info.entry_actions]}"
        )
    if state_info.fixed_transitions:
        print("  Transitions:")
        for trans in state_info.fixed_transitions:
            params = (
                f" ({trans.trigger.parameter_types})"
                if trans.trigger.parameter_types
                else ""
            )
            print(
                f"    - {trans.trigger.underlying_trigger}{params} -> {trans.destination_state}"
            )
    if state_info.reentry_transitions:  # Assuming reflection adds this
        print("  Reentry Transitions:")
        for trans in state_info.reentry_transitions:
            params = (
                f" ({trans.trigger.parameter_types})"
                if trans.trigger.parameter_types
                else ""
            )
            print(f"    - {trans.trigger.underlying_trigger}{params}")

# --- Graph Generation ---
try:
    print("\nGenerating graph...")
    bug.state_machine.visualize("bug_tracker.png", view=False)
    print("Graph saved to bug_tracker.png")
except Exception as e:
    print(f"Could not generate graph: {e}")
