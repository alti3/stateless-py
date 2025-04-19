import pytest
from enum import Enum, auto

from stateless import StateMachine, InvalidTransitionError

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()


class Trigger(Enum):
    X = auto()


# --- Sync Guards ---


def test_permit_if_sync_guard_met() -> None:
    """Tests permit_if with a synchronous guard that passes."""
    guard_called = False

    def guard() -> bool:
        nonlocal guard_called
        guard_called = True
        return True

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard, "Guard Description")

    sm.fire(Trigger.X)
    assert sm.state == State.B
    assert guard_called is True


def test_permit_if_sync_guard_not_met() -> None:
    """Tests permit_if with a synchronous guard that fails."""
    guard_called = False

    def guard() -> bool:
        nonlocal guard_called
        guard_called = True
        return False

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard, "Guard Description")

    with pytest.raises(InvalidTransitionError) as excinfo:
        sm.fire(Trigger.X)
    assert sm.state == State.A  # State should not change
    assert guard_called is True
    assert "guard conditions were not met" in str(excinfo.value)
    assert "Guard Description" in str(excinfo.value)


def test_multiple_sync_guards_all_met() -> None:
    """Tests multiple synchronous guards that all pass."""
    guards_called = [False, False]

    def guard1():
        guards_called[0] = True
        return True

    def guard2():
        guards_called[1] = True
        return True

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(
        Trigger.X, State.B, guards=[(guard1, "G1"), (guard2, "G2")]
    )

    sm.fire(Trigger.X)
    assert sm.state == State.B
    assert all(guards_called)


def test_multiple_sync_guards_one_not_met() -> None:
    """Tests multiple synchronous guards where one fails."""
    guards_called = [False, False]

    def guard1():
        guards_called[0] = True
        return True

    def guard2():
        guards_called[1] = True
        return False  # This one fails

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(
        Trigger.X, State.B, guards=[(guard1, "G1"), (guard2, "G2")]
    )

    with pytest.raises(InvalidTransitionError) as excinfo:
        sm.fire(Trigger.X)
    assert sm.state == State.A
    assert guards_called == [True, True]  # Both should be called
    assert "G2" in str(excinfo.value)  # Failed guard description
    assert "G1" not in str(excinfo.value)  # Met guard description


def test_sync_guard_with_args() -> None:
    """Tests passing trigger arguments to a synchronous guard."""
    guard_args = None

    def guard(a: int, b: str) -> bool:
        nonlocal guard_args
        guard_args = (a, b)
        return a > 10 and b == "go"

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard)

    # Guard fails
    with pytest.raises(InvalidTransitionError):
        sm.fire(Trigger.X, 5, "go")
    assert guard_args == (5, "go")
    assert sm.state == State.A

    # Guard passes
    sm.fire(Trigger.X, 15, "go")
    assert guard_args == (15, "go")
    assert sm.state == State.B


# --- Async Guards ---


@pytest.mark.asyncio
async def test_permit_if_async_guard_met() -> None:
    """Tests permit_if with an async guard that passes, using fire_async."""
    guard_called = False

    async def guard() -> bool:
        nonlocal guard_called
        guard_called = True
        return True

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(
        Trigger.X, State.B, guard
    )  # permit_if handles async

    await sm.fire_async(Trigger.X)
    assert sm.state == State.B
    assert guard_called is True


@pytest.mark.asyncio
async def test_permit_if_async_guard_not_met() -> None:
    """Tests permit_if with an async guard that fails, using fire_async."""
    guard_called = False

    async def guard() -> bool:
        nonlocal guard_called
        guard_called = True
        return False

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard, "Async Guard")

    with pytest.raises(InvalidTransitionError) as excinfo:
        await sm.fire_async(Trigger.X)
    assert sm.state == State.A
    assert guard_called is True
    assert "Async Guard" in str(excinfo.value)


@pytest.mark.asyncio
async def test_multiple_mixed_guards_met() -> None:
    """Tests a mix of sync and async guards that all pass."""
    guards_called = [False, False]

    def guard1() -> bool:
        guards_called[0] = True
        return True

    async def guard2() -> bool:
        guards_called[1] = True
        return True

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(
        Trigger.X, State.B, guards=[(guard1, "G1"), (guard2, "G2")]
    )

    await sm.fire_async(Trigger.X)
    assert sm.state == State.B
    assert all(guards_called)


@pytest.mark.asyncio
async def test_multiple_mixed_guards_async_fail() -> None:
    """Tests a mix of sync and async guards where the async one fails."""
    guards_called = [False, False]

    def guard1():
        guards_called[0] = True
        return True

    async def guard2() -> bool:
        guards_called[1] = True
        return False  # Fails

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(
        Trigger.X, State.B, guards=[(guard1, "G1"), (guard2, "G2")]
    )

    with pytest.raises(InvalidTransitionError) as excinfo:
        await sm.fire_async(Trigger.X)
    assert sm.state == State.A
    assert guards_called == [True, True]  # Both should be called
    assert "G2" in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_guard_with_args() -> None:
    """Tests passing trigger arguments to an async guard."""
    guard_args = None

    async def guard(x: int) -> bool:
        nonlocal guard_args
        guard_args = x
        return x > 0

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard)

    with pytest.raises(InvalidTransitionError):
        await sm.fire_async(Trigger.X, -5)
    assert guard_args == -5
    assert sm.state == State.A

    await sm.fire_async(Trigger.X, 5)
    assert guard_args == 5
    assert sm.state == State.B


# --- Sync/Async Mismatch ---


def test_fire_sync_with_async_guard_raises_type_error() -> None:
    """Tests that fire() raises TypeError if an async guard is encountered."""

    async def guard() -> bool:
        return True

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard)

    with pytest.raises(TypeError) as excinfo:
        sm.fire(Trigger.X)
    assert "synchronously" in str(excinfo.value)
    assert "async functions" in str(excinfo.value)


def test_can_fire_sync_with_async_guard_raises_type_error() -> None:
    """Tests that can_fire() raises TypeError if an async guard is encountered."""

    async def guard() -> bool:
        return True

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard)

    with pytest.raises(TypeError) as excinfo:
        sm.can_fire(Trigger.X)
    assert "synchronously" in str(excinfo.value)
    assert "async guards" in str(excinfo.value)


def test_get_permitted_triggers_sync_skips_async_guards() -> None:
    """Tests that get_permitted_triggers() skips triggers with async guards."""

    async def guard_async() -> bool:
        return True

    def guard_sync() -> bool:
        return True

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard_async)  # Async guard
    sm.configure(State.A).permit_if(Trigger.Y, State.C, guard_sync)  # Sync guard

    permitted = sm.get_permitted_triggers()
    assert permitted == [Trigger.Y]  # Only Y should be permitted in sync check
