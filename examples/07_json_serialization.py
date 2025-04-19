import json
from enum import Enum, auto
from typing import Any

from stateless import StateMachine


# --- States & Triggers ---
class MembershipState(Enum):
    INACTIVE = auto()
    ACTIVE = auto()
    TERMINATED = auto()


class MemberTriggers(Enum):
    SUSPEND = auto()
    TERMINATE = auto()
    REACTIVATE = auto()


# --- Member Class ---
class Member:
    def __init__(
        self, name: str, initial_state: MembershipState = MembershipState.ACTIVE
    ):
        self.name = name
        self._state = initial_state
        # State machine configured on initialization or deserialization
        self._state_machine = self._configure_state_machine(initial_state)

    @property
    def state(self) -> MembershipState:
        # Always get state from the machine after initialization
        return self._state_machine.state

    def _set_state(self, new_state: MembershipState):
        print(f"Member '{self.name}': State changing from {self._state} to {new_state}")
        self._state = new_state

    def _configure_state_machine(
        self, current_state: MembershipState
    ) -> StateMachine[MembershipState, MemberTriggers]:
        """Configures and returns a state machine instance."""
        sm = StateMachine[MembershipState, MemberTriggers](
            current_state,
            state_accessor=lambda: self._state,
            state_mutator=self._set_state,
        )

        sm.configure(MembershipState.ACTIVE).permit(
            MemberTriggers.SUSPEND, MembershipState.INACTIVE
        ).permit(MemberTriggers.TERMINATE, MembershipState.TERMINATED)

        sm.configure(MembershipState.INACTIVE).permit(
            MemberTriggers.REACTIVATE, MembershipState.ACTIVE
        ).permit(MemberTriggers.TERMINATE, MembershipState.TERMINATED)

        sm.configure(MembershipState.TERMINATED).permit(
            MemberTriggers.REACTIVATE, MembershipState.ACTIVE
        )  # Allow reactivation from terminated

        return sm

    # --- Public methods to fire triggers ---
    def terminate(self) -> None:
        print(f"\nAttempting to Terminate '{self.name}'...")
        self._state_machine.fire(MemberTriggers.TERMINATE)

    def suspend(self) -> None:
        print(f"\nAttempting to Suspend '{self.name}'...")
        self._state_machine.fire(MemberTriggers.SUSPEND)

    def reactivate(self) -> None:
        print(f"\nAttempting to Reactivate '{self.name}'...")
        self._state_machine.fire(MemberTriggers.REACTIVATE)

    # --- Serialization ---
    def to_dict(self) -> dict[str, Any]:
        """Serialize relevant data to a dictionary."""
        return {
            "name": self.name,
            "state": self.state.name,  # Store state name as string
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Member":
        """Deserialize from a dictionary."""
        name = data.get("name")
        state_name = data.get("state")
        if not name or not state_name:
            raise ValueError("Invalid data for Member deserialization")

        try:
            # Convert state name back to Enum member
            initial_state = MembershipState[state_name]
        except KeyError:
            raise ValueError(f"Invalid state name '{state_name}'")

        # Create instance with the deserialized state
        return cls(name=name, initial_state=initial_state)

    def to_json(self) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_string: str) -> "Member":
        """Deserialize from a JSON string."""
        data = json.loads(json_string)
        return cls.from_dict(data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Member):
            return NotImplemented
        return self.name == other.name and self.state == other.state

    def __str__(self) -> str:
        return f"Member(Name: '{self.name}', State: {self.state.name})"


# --- Usage ---
print("Creating member 'Alice'")
member1 = Member("Alice")
print(member1)

member1.suspend()
print(member1)

member1.terminate()
print(member1)

print("\nSerializing member1 to JSON:")
json_data = member1.to_json()
print(json_data)

print("\nDeserializing from JSON:")
member2 = Member.from_json(json_data)
print(f"Deserialized member: {member2}")

print(f"\nAre member1 and member2 equal? {member1 == member2}")

print("\nReactivating deserialized member:")
member2.reactivate()
print(member2)

print(f"\nAre member1 and member2 equal now? {member1 == member2}")

# Example of creating from JSON with a specific initial state
print("\nCreating member 'Bob' from JSON (Inactive state):")
bob_json = '{ "name": "Bob", "state": "INACTIVE" }'
member_bob = Member.from_json(bob_json)
print(member_bob)
member_bob.reactivate()
print(member_bob)
