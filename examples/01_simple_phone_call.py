from enum import Enum, auto
from stateless import StateMachine


# --- States ---
class State(Enum):
    OFF_HOOK = auto()
    RINGING = auto()
    CONNECTED = auto()
    ON_HOLD = auto()
    PHONE_DESTROYED = auto()  # Added for illustration


# --- Triggers ---
class Trigger(Enum):
    CALL_DIALED = auto()
    CALL_CONNECTED = auto()
    LEFT_MESSAGE = auto()
    PLACED_ON_HOLD = auto()
    TAKEN_OFF_HOLD = auto()
    HUNG_UP = auto()
    SMASHED_WITH_HAMMER = auto()  # Added


# --- State Machine Setup ---
phone_call = StateMachine[State, Trigger](State.OFF_HOOK)

# --- Configuration ---
phone_call.configure(State.OFF_HOOK).permit(Trigger.CALL_DIALED, State.RINGING)

phone_call.configure(State.RINGING).permit(
    Trigger.CALL_CONNECTED, State.CONNECTED
).permit(Trigger.HUNG_UP, State.OFF_HOOK)

phone_call.configure(State.CONNECTED).permit(
    Trigger.LEFT_MESSAGE, State.OFF_HOOK
).permit(Trigger.HUNG_UP, State.OFF_HOOK).permit(Trigger.PLACED_ON_HOLD, State.ON_HOLD)

phone_call.configure(State.ON_HOLD).permit(
    Trigger.TAKEN_OFF_HOLD, State.CONNECTED
).permit(Trigger.HUNG_UP, State.OFF_HOOK)

# Example of configuring a transition from any state
# Note: stateless-py doesn't have a direct equivalent to PermitReentryIf across all states.
# You would typically configure this on relevant states or handle it externally.
# For illustration, let's add a "destroy" transition from a few states:
phone_call.configure(State.OFF_HOOK).permit(
    Trigger.SMASHED_WITH_HAMMER, State.PHONE_DESTROYED
)
phone_call.configure(State.RINGING).permit(
    Trigger.SMASHED_WITH_HAMMER, State.PHONE_DESTROYED
)
phone_call.configure(State.CONNECTED).permit(
    Trigger.SMASHED_WITH_HAMMER, State.PHONE_DESTROYED
)
phone_call.configure(State.ON_HOLD).permit(
    Trigger.SMASHED_WITH_HAMMER, State.PHONE_DESTROYED
)


# --- Usage ---
def print_state(sm: StateMachine):
    print(f"[{sm.state}]")


print("Initial State:")
print_state(phone_call)

print("\nDialing...")
phone_call.fire(Trigger.CALL_DIALED)
print_state(phone_call)

print("\nConnecting...")
phone_call.fire(Trigger.CALL_CONNECTED)
print_state(phone_call)

print("\nPlacing on hold...")
phone_call.fire(Trigger.PLACED_ON_HOLD)
print_state(phone_call)

print("\nTaking off hold...")
phone_call.fire(Trigger.TAKEN_OFF_HOLD)
print_state(phone_call)

print("\nHanging up...")
phone_call.fire(Trigger.HUNG_UP)
print_state(phone_call)

print("\nDialing again...")
phone_call.fire(Trigger.CALL_DIALED)
print_state(phone_call)

print("\nSmashing phone...")
phone_call.fire(Trigger.SMASHED_WITH_HAMMER)
print_state(phone_call)

# Try firing after destruction (should fail if not configured)
try:
    print("\nTrying to dial destroyed phone...")
    phone_call.fire(Trigger.CALL_DIALED)
except Exception as e:
    print(f"Error: {e}")
print_state(phone_call)

# --- Introspection Example ---
print("\n--- State Machine Info ---")
info = phone_call.get_info()
print(f"Initial State: {info.initial_state}")
for state_info in info.states:
    print(f"\nState: {state_info.underlying_state}")
    if state_info.fixed_transitions:
        print("  Transitions:")
        for trans in state_info.fixed_transitions:
            guards = (
                f" (Guards: {len(trans.guard_conditions)})"
                if trans.guard_conditions
                else ""
            )
            print(
                f"    - {trans.trigger.underlying_trigger} -> {trans.destination_state}{guards}"
            )

# --- Graph Generation Example ---
# Requires graphviz installed: pip install graphviz
# And the dot executable in your system's PATH
try:
    print("\nGenerating graph...")
    phone_call.visualize("phone_call.png", view=False)
    print("Graph saved to phone_call.png")
except Exception as e:
    print(f"Could not generate graph: {e}")
    print("(Ensure graphviz is installed and the 'dot' command is in your PATH)")
