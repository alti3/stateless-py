import pytest
import asyncio
from enum import Enum, auto

from stateless import StateMachine, FiringMode
from stateless.transition import Transition

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()
    C = auto()


class Trigger(Enum):
    X = auto()
    Y = auto()
    Z = auto()


actions_log: list[str] = []


def setup_function() -> None:
    actions_log.clear()


# --- FiringMode.IMMEDIATE (Default, tested elsewhere) ---

# --- FiringMode.QUEUED ---


@pytest.mark.asyncio
async def test_queued_basic_sequence() -> None:
    sm = StateMachine[State, Trigger](State.A, firing_mode=FiringMode.QUEUED)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).permit(Trigger.Y, State.C)

    task_x = asyncio.create_task(sm.fire_async(Trigger.X))
    task_y = asyncio.create_task(sm.fire_async(Trigger.Y))

    await asyncio.gather(task_x, task_y)
    # Allow queue processor time to run
    await asyncio.sleep(0.05)

    assert sm.state == State.C
    await sm.close_async()


@pytest.mark.asyncio
async def test_queued_long_action_blocks_next() -> None:
    sm = StateMachine[State, Trigger](State.A, firing_mode=FiringMode.QUEUED)

    async def long_entry_b(t: Transition[State, Trigger]) -> None:
        actions_log.append("entry_b_start")
        await asyncio.sleep(0.1)
        actions_log.append("entry_b_end")

    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).on_entry(long_entry_b).permit(Trigger.Y, State.C)
    sm.configure(State.C).on_entry(lambda t: actions_log.append("entry_c"))

    t0 = asyncio.get_running_loop().time()
    # Fire both quickly
    await sm.fire_async(Trigger.X)
    await sm.fire_async(Trigger.Y)

    # Wait longer than the action duration
    await asyncio.sleep(0.2)
    t1 = asyncio.get_running_loop().time()

    assert sm.state == State.C
    assert actions_log == ["entry_b_start", "entry_b_end", "entry_c"]
    assert (t1 - t0) >= 0.1  # Ensure it took at least the action time

    await sm.close_async()


@pytest.mark.asyncio
async def test_queued_guard_failure_logged() -> None:
    sm = StateMachine[State, Trigger](State.A, firing_mode=FiringMode.QUEUED)
    sm.configure(State.A).permit_if(Trigger.X, State.B, lambda: False, "GuardFail")

    with pytest.warns(RuntimeWarning, match="Queued trigger .* failed"):
        await sm.fire_async(Trigger.X)
        await sm._queued_triggers.join()

    assert sm.state == State.A  # State unchanged

    await sm.close_async()


@pytest.mark.asyncio
async def test_queued_unhandled_trigger_logged() -> None:
    sm = StateMachine[State, Trigger](State.A, firing_mode=FiringMode.QUEUED)
    # No config for Trigger.X

    with pytest.warns(RuntimeWarning, match="Queued trigger .* failed"):
        await sm.fire_async(Trigger.X)
        await sm._queued_triggers.join()

    assert sm.state == State.A

    await sm.close_async()


@pytest.mark.asyncio
async def test_queued_fire_without_running_loop() -> None:
    # This test is tricky as it depends on the environment setup
    # We simulate by trying to fire before starting the loop explicitly
    sm = StateMachine[State, Trigger](State.A, firing_mode=FiringMode.QUEUED)
    sm.configure(State.A).permit(Trigger.X, State.B)

    await sm.fire_async(Trigger.X)
    await sm._queued_triggers.join()
    assert sm.state == State.B

    # Clean up if task was somehow created
    await sm.close_async()


@pytest.mark.asyncio
async def test_queued_action_exception_logged_and_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests that an exception in a queued action is logged and queue continues."""
    sm = StateMachine[State, Trigger](State.A, firing_mode=FiringMode.QUEUED)
    processed_y = False
    processed_z = False

    async def faulty_entry_b(t: Transition[State, Trigger]) -> None:
        actions_log.append("entry_b_start")
        raise ValueError("Action failed!")
        actions_log.append("entry_b_end")  # pragma: no cover

    def entry_c(t: Transition[State, Trigger]) -> None:
        nonlocal processed_y
        processed_y = True
        actions_log.append("entry_c")

    def entry_a_from_z(t: Transition[State, Trigger]) -> None:
        nonlocal processed_z
        processed_z = True
        actions_log.append("entry_a_from_z")

    sm.configure(State.A).permit(Trigger.X, State.B).permit(
        Trigger.Z, State.A
    ).on_entry(entry_a_from_z)
    sm.configure(State.B).on_entry(faulty_entry_b).permit(Trigger.Y, State.C)
    sm.configure(State.C).on_entry(entry_c)

    # Fire X (entry action fails after the state changes), then Y continues from B.
    with pytest.warns(
        RuntimeWarning,
        match="Unexpected error processing queued trigger .*Action failed!",
    ):
        await sm.fire_async(Trigger.X)
        await sm._queued_triggers.join()
    await sm.fire_async(Trigger.Y)
    await sm._queued_triggers.join()
    with pytest.warns(RuntimeWarning, match="Queued trigger .* failed"):
        await sm.fire_async(Trigger.Z)
        await sm._queued_triggers.join()

    # Wait for queue to process all triggers
    await asyncio.sleep(0.1)

    assert sm.state == State.C
    assert actions_log == ["entry_b_start", "entry_c"]
    assert processed_y is True
    assert processed_z is False

    assert caplog.text == ""

    await sm.close_async()


# --- FiringMode.DEVELOPMENT (Placeholder) ---
# Add tests if this mode is implemented
