from enum import Enum, auto

from stateless import StateMachine, Transition


# --- States ---
class State(Enum):
    A = auto()
    B = auto()


# --- Triggers ---
class Trigger(Enum):
    STEP = auto()
    IGNORE_ME = auto()
    REENTER = auto()


# --- Log ---
log: list[str] = []


# --- Actions ---
def on_entry(state_name: str):
    def action(t: Transition):
        log.append(f"Entered {state_name} from {t.trigger}")

    return action


def on_exit(state_name: str):
    def action(t: Transition):
        log.append(f"Exited {state_name} via {t.trigger}")

    return action


# --- State Machine Setup ---
sm = StateMachine[State, Trigger](State.A)

sm.configure(State.A).on_entry(on_entry("A")).on_exit(on_exit("A")).permit(
    Trigger.STEP, State.B
).ignore(Trigger.IGNORE_ME).permit_reentry(Trigger.REENTER)

sm.configure(State.B).on_entry(on_entry("B")).on_exit(on_exit("B")).permit(
    Trigger.STEP, State.A
)


# --- Usage ---
def print_log_and_state(message: str):
    print(f"\n--- {message} ---")
    print(f"Current State: {sm.state}")
    print("Log:")
    for entry in log:
        print(f"  - {entry}")
    log.clear()  # Clear log after printing for next step


# Initial state entry isn't logged by default in this setup
print(f"Initial State: {sm.state}")

# Ignore
sm.fire(Trigger.IGNORE_ME)
print_log_and_state("After firing IGNORE_ME")  # Should be empty log, state A

# Reentry
sm.fire(Trigger.REENTER)
print_log_and_state("After firing REENTER")  # Should log Exit A, Entry A; state A

# Step to B
sm.fire(Trigger.STEP)
print_log_and_state("After firing STEP (to B)")  # Should log Exit A, Entry B; state B

# Try Ignore in B (not configured, should raise error)
try:
    sm.fire(Trigger.IGNORE_ME)
except Exception as e:
    print(f"\nError firing IGNORE_ME in State B: {e}")
print_log_and_state("After trying IGNORE_ME in B")  # Should be empty log, state B

# Step back to A
sm.fire(Trigger.STEP)
print_log_and_state("After firing STEP (to A)")  # Should log Exit B, Entry A; state A
