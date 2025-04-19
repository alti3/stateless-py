import pytest  # Using pytest markers for async tests
import asyncio
from enum import Enum, auto

from stateless import StateMachine, Transition


# --- States ---
class State(Enum):
    STARTING = auto()
    EXECUTING = auto()
    FINISHED = auto()


# --- Triggers ---
class Trigger(Enum):
    START = auto()
    FINISH = auto()


# --- Log ---
log: list[str] = []


# --- Async Actions ---
async def on_entry_executing(transition: Transition[State, Trigger]) -> None:
    log.append(f"Entering {transition.destination}...")
    await asyncio.sleep(0.1)  # Simulate async work
    log.append(f"Async work in {transition.destination} complete.")


async def on_exit_executing(transition: Transition[State, Trigger]) -> None:
    log.append(f"Exiting {transition.source}...")
    await asyncio.sleep(0.05)  # Simulate async cleanup
    log.append(f"Async cleanup in {transition.source} complete.")


async def on_entry_finished(transition: Transition[State, Trigger]) -> None:
    log.append(f"Entering {transition.destination}. Process complete.")


# --- State Machine Setup ---
async_machine = StateMachine[State, Trigger](State.STARTING)

async_machine.configure(State.STARTING).permit(Trigger.START, State.EXECUTING)

async_machine.configure(State.EXECUTING).on_entry_async(
    on_entry_executing
).on_exit_async(on_exit_executing).permit(Trigger.FINISH, State.FINISHED)

async_machine.configure(State.FINISHED).on_entry_async(on_entry_finished)


# --- Usage ---
@pytest.mark.asyncio  # Use pytest-asyncio runner if running as test
async def main() -> None:
    print("Initial State:", async_machine.state)
    log.append(f"Initial State: {async_machine.state}")

    print("\nFiring START...")
    log.append("Firing START")
    await async_machine.fire_async(Trigger.START)
    print("Current State:", async_machine.state)
    log.append(f"Current State: {async_machine.state}")

    # Give some time for entry action to potentially progress if needed
    await asyncio.sleep(0.01)

    print("\nFiring FINISH...")
    log.append("Firing FINISH")
    await async_machine.fire_async(Trigger.FINISH)
    print("Current State:", async_machine.state)
    log.append(f"Current State: {async_machine.state}")

    print("\n--- Execution Log ---")
    for entry in log:
        print(entry)

    # Verify expected log order (approximate)
    expected_order = [
        "Initial State: State.STARTING",
        "Firing START",
        "Entering State.EXECUTING...",  # Start entry B
        "Async work in State.EXECUTING complete.",  # Finish entry B
        "Current State: State.EXECUTING",
        "Firing FINISH",
        "Exiting State.EXECUTING...",  # Start exit B
        "Async cleanup in State.EXECUTING complete.",  # Finish exit B
        "Entering State.FINISHED. Process complete.",  # Entry C
        "Current State: State.FINISHED",
    ]
    # Note: Exact timing isn't guaranteed, but sequence should hold
    assert log == expected_order, (
        f"Log mismatch:\nExpected: {expected_order}\nActual: {log}"
    )


if __name__ == "__main__":
    asyncio.run(main())
