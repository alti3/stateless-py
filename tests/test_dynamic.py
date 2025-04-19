import pytest
from enum import Enum, auto

from stateless import StateMachine, InvalidTransitionError

# TODO: Add tests for dynamic transitions

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()
    C = auto()
    D = auto()  # Target for dynamic


class Trigger(Enum):
    DYNAMIC_MOVE = auto()


actions_log: list[str] = []


def setup_function() -> None:
    actions_log.clear()


# --- Sync Selector ---


def test_dynamic_sync_selector() -> None:
    target_state = State.C

    def selector() -> State:
        actions_log.append(f"selector_called_returns_{target_state.name}")
        return target_state

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).dynamic(Trigger.DYNAMIC_MOVE, selector)

    sm.fire(Trigger.DYNAMIC_MOVE)
    assert sm.state == State.C
    assert actions_log == ["selector_called_returns_C"]

    actions_log.clear()
    target_state = State.D  # Change selector result
    sm.fire(Trigger.DYNAMIC_MOVE)
    assert sm.state == State.D
    assert actions_log == ["selector_called_returns_D"]


def test_dynamic_sync_selector_with_args() -> None:
    selector_args = None

    def selector(arg1: int, arg2: bool) -> State:
        nonlocal selector_args
        selector_args = (arg1, arg2)
        return State.C if arg1 > 0 and arg2 else State.D

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).dynamic(Trigger.DYNAMIC_MOVE, selector)

    sm.fire(Trigger.DYNAMIC_MOVE, 10, True)
    assert sm.state == State.C
    assert selector_args == (10, True)

    sm.fire(Trigger.DYNAMIC_MOVE, -5, True)
    assert sm.state == State.D
    assert selector_args == (-5, True)

    sm.fire(Trigger.DYNAMIC_MOVE, 10, False)
    assert sm.state == State.D
    assert selector_args == (10, False)


# --- Async Selector ---


@pytest.mark.asyncio
async def test_dynamic_async_selector() -> None:
    target_state = State.C

    async def selector():
        actions_log.append(f"async_selector_called_returns_{target_state.name}")
        return target_state

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).dynamic(Trigger.DYNAMIC_MOVE, selector)

    await sm.fire_async(Trigger.DYNAMIC_MOVE)
    assert sm.state == State.C
    assert actions_log == ["async_selector_called_returns_C"]


@pytest.mark.asyncio
async def test_dynamic_async_selector_with_args() -> None:
    selector_args = None

    async def selector(name: str) -> State:
        nonlocal selector_args
        selector_args = name
        return State.C if name == "target_c" else State.D

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).dynamic(Trigger.DYNAMIC_MOVE, selector)

    await sm.fire_async(Trigger.DYNAMIC_MOVE, "target_c")
    assert sm.state == State.C
    assert selector_args == "target_c"

    await sm.fire_async(Trigger.DYNAMIC_MOVE, "other")
    assert sm.state == State.D
    assert selector_args == "other"


# --- Guards with Dynamic ---


@pytest.mark.asyncio
async def test_dynamic_with_guard_met() -> None:
    guard_called = False

    def guard() -> bool:
        nonlocal guard_called
        guard_called = True
        return True

    def selector() -> State:
        return State.C

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).dynamic(Trigger.DYNAMIC_MOVE, selector, guard=guard)

    await sm.fire_async(Trigger.DYNAMIC_MOVE)
    assert sm.state == State.C
    assert guard_called is True


@pytest.mark.asyncio
async def test_dynamic_with_guard_not_met() -> None:
    guard_called = False
    selector_called = False

    def guard() -> bool:
        nonlocal guard_called
        guard_called = True
        return False

    def selector() -> State:
        nonlocal selector_called
        selector_called = True
        return State.C

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).dynamic(
        Trigger.DYNAMIC_MOVE, selector, guard=guard, guard_description="DynamicGuard"
    )

    with pytest.raises(InvalidTransitionError) as excinfo:
        await sm.fire_async(Trigger.DYNAMIC_MOVE)
    assert sm.state == State.A
    assert guard_called is True
    assert selector_called is False  # Selector should not be called if guard fails
    assert "DynamicGuard" in str(excinfo.value)


# --- Sync/Async Mismatch ---


def test_fire_sync_with_async_selector_raises_type_error() -> None:
    async def selector() -> State:
        return State.C

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).dynamic(Trigger.DYNAMIC_MOVE, selector)

    with pytest.raises(TypeError) as excinfo:
        sm.fire(Trigger.DYNAMIC_MOVE)
    assert "synchronously" in str(excinfo.value)
    assert "Dynamic destination function" in str(excinfo.value)
