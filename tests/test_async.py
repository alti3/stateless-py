import pytest
import asyncio
from enum import Enum, auto
from typing import List, Sequence, Any

from stateless import StateMachine, Transition, InvalidTransitionError, FiringMode

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()
    C = auto()


class Trigger(Enum):
    X = auto()
    Y = auto()
    Z = auto()


actions_log: List[str] = []


def setup_function():
    actions_log.clear()


# --- Async Combinations ---


@pytest.mark.asyncio
async def test_async_guard_and_async_action():
    """Tests transition with both async guard and async action."""

    async def guard():
        actions_log.append("guard_check")
        await asyncio.sleep(0.01)
        return True

    async def entry_b(t):
        actions_log.append("entry_b_start")
        await asyncio.sleep(0.01)
        actions_log.append("entry_b_end")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard)
    sm.configure(State.B).on_entry(entry_b)

    await sm.fire_async(Trigger.X)
    assert sm.state == State.B
    assert actions_log == ["guard_check", "entry_b_start", "entry_b_end"]


@pytest.mark.asyncio
async def test_can_fire_async():
    """Tests can_fire_async with sync and async guards."""

    async def guard_async_true():
        return True

    async def guard_async_false():
        return False

    def guard_sync_true():
        return True

    def guard_sync_false():
        return False

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard_async_true)  # Async True
    sm.configure(State.A).permit_if(
        Trigger.Y, State.B, guard_async_false
    )  # Async False
    sm.configure(State.A).permit_if(Trigger.Z, State.B, guard_sync_true)  # Sync True
    sm.configure(State.B).permit_if(
        Trigger.X, State.A, guard_sync_false
    )  # Sync False (wrong state)

    assert await sm.can_fire_async(Trigger.X) is True
    assert await sm.can_fire_async(Trigger.Y) is False
    assert await sm.can_fire_async(Trigger.Z) is True
    assert (
        await sm.can_fire_async(Trigger.X, 1, 2) is True
    )  # Args shouldn't affect if guard takes none

    # Test trigger valid in different state
    sm.fire(Trigger.Z)  # Move to B sync
    assert sm.state == State.B
    assert await sm.can_fire_async(Trigger.X) is False  # Guard is false in B


@pytest.mark.asyncio
async def test_get_permitted_triggers_async():
    """Tests get_permitted_triggers_async."""

    async def guard_async_true():
        return True

    async def guard_async_false():
        return False

    def guard_sync_true():
        return True

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard_async_true)
    sm.configure(State.A).permit_if(Trigger.Y, State.B, guard_async_false)
    sm.configure(State.A).permit_if(Trigger.Z, State.B, guard_sync_true)
    sm.configure(State.B).permit(Trigger.X, State.A)  # X permitted in B

    permitted = await sm.get_permitted_triggers_async()
    assert set(permitted) == {Trigger.X, Trigger.Z}  # Y guard fails


# --- FiringMode.QUEUED ---


@pytest.mark.asyncio
async def test_queued_firing_mode_immediate_sync_raises():
    """Tests fire() raises error in QUEUED mode."""
    sm = StateMachine[State, Trigger](State.A, firing_mode=FiringMode.QUEUED)
    sm.configure(State.A).permit(Trigger.X, State.B)
    with pytest.raises(
        Exception
    ) as excinfo:  # Using base Exception as StatelessError might not be raised yet
        sm.fire(Trigger.X)
    assert "Cannot fire synchronously when FiringMode is QUEUED" in str(excinfo.value)
    await sm.close_async()  # Cleanup task


@pytest.mark.asyncio
async def test_queued_firing_mode_processes_sequentially():
    """Tests that queued triggers are processed in order."""
    sm = StateMachine[State, Trigger](State.A, firing_mode=FiringMode.QUEUED)

    async def entry_b(t):
        actions_log.append("entry_b_start")
        await asyncio.sleep(0.05)  # Make it take time
        actions_log.append("entry_b_end")

    async def entry_c(t):
        actions_log.append("entry_c_start")
        await asyncio.sleep(0.01)
        actions_log.append("entry_c_end")

    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).on_entry(entry_b).permit(Trigger.Y, State.C)
    sm.configure(State.C).on_entry(entry_c)

    # Fire multiple triggers quickly
    await sm.fire_async(Trigger.X)  # A -> B (takes 0.05s in entry)
    await sm.fire_async(Trigger.Y)  # B -> C (should wait for X to finish)
    await sm.fire_async(Trigger.Z)  # Unhandled (should be logged/handled after Y)

    # Wait for queue to likely process
    await asyncio.sleep(0.2)

    # Check state and action order
    assert sm.state == State.C
    assert actions_log == [
        "entry_b_start",
        "entry_b_end",  # X finishes
        "entry_c_start",
        "entry_c_end",  # Y finishes
        # Z is unhandled, check log output or handler if configured
    ]
    # Check queue is empty (requires access or specific test method)
    # assert sm._queue.empty() # Not directly testable without modification

    await sm.close_async()  # Cleanup task


@pytest.mark.asyncio
async def test_queued_firing_mode_guard_failure():
    """Tests guard failure in queued mode."""
    sm = StateMachine[State, Trigger](State.A, firing_mode=FiringMode.QUEUED)
    can_y = False

    def guard_y():
        return can_y

    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).permit_if(Trigger.Y, State.C, guard_y)

    await sm.fire_async(Trigger.X)  # A -> B
    await sm.fire_async(Trigger.Y)  # B -> C (guard fails initially)

    await asyncio.sleep(0.1)  # Let X process
    assert sm.state == State.B  # Should be in B, Y failed
    # Check logs for InvalidTransitionError related to Y

    can_y = True  # Allow Y now
    await sm.fire_async(Trigger.Y)  # Fire Y again

    await asyncio.sleep(0.1)  # Let Y process
    assert sm.state == State.C  # Should now be in C

    await sm.close_async()
