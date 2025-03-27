import pytest
from enum import Enum, auto
from typing import List

from stateless import StateMachine, InvalidTransitionError

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()


class Trigger(Enum):
    IGNORED = auto()
    GUARDED_IGNORE = auto()
    MOVE = auto()


actions_log: List[str] = []


def setup_function():
    actions_log.clear()


def entry(s):
    return lambda t: actions_log.append(f"entry_{s.name}")


def exit_(s):
    return lambda t: actions_log.append(f"exit_{s.name}")


# --- Basic Ignore ---


@pytest.mark.asyncio
async def test_ignore_trigger():
    """Tests that an ignored trigger does nothing."""
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_exit(exit_(State.A)).ignore(Trigger.IGNORED).permit(
        Trigger.MOVE, State.B
    )

    await sm.fire_async(Trigger.IGNORED)
    assert sm.state == State.A  # State unchanged
    assert actions_log == []  # No actions executed

    # Ensure other triggers still work
    await sm.fire_async(Trigger.MOVE)
    assert sm.state == State.B
    assert actions_log == ["exit_State.A"]


# --- Ignore with Guards ---


@pytest.mark.asyncio
async def test_ignore_if_guard_met():
    """Tests ignore_if when the guard passes."""
    should_ignore = True

    def guard():
        return should_ignore

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).ignore_if(Trigger.GUARDED_IGNORE, guard).permit(
        Trigger.MOVE, State.B
    )  # Ensure permit doesn't override ignore

    await sm.fire_async(Trigger.GUARDED_IGNORE)
    assert sm.state == State.A
    assert actions_log == []


@pytest.mark.asyncio
async def test_ignore_if_guard_not_met_falls_through():
    """Tests ignore_if when the guard fails, allowing other handlers."""
    should_ignore = False

    def guard():
        return should_ignore

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).ignore_if(Trigger.GUARDED_IGNORE, guard).permit(
        Trigger.GUARDED_IGNORE, State.B
    )  # Permit same trigger if guard fails

    await sm.fire_async(Trigger.GUARDED_IGNORE)
    assert sm.state == State.B  # Should transition via permit


@pytest.mark.asyncio
async def test_ignore_if_guard_not_met_unhandled():
    """Tests ignore_if when guard fails and no other handler exists."""
    should_ignore = False

    def guard():
        return should_ignore

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).ignore_if(Trigger.GUARDED_IGNORE, guard)
    # No other handler for GUARDED_IGNORE

    with pytest.raises(InvalidTransitionError) as excinfo:
        await sm.fire_async(Trigger.GUARDED_IGNORE)
    assert "No valid transitions permitted" in str(excinfo.value)
    assert sm.state == State.A
