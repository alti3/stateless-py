import pytest
from enum import Enum, auto
from typing import List, Sequence, Any

from stateless import StateMachine, Transition, InvalidTransitionError

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()


class Trigger(Enum):
    X = auto()
    Y = auto()


actions_log: List[Any] = []
guard_log: List[Any] = []
selector_log: List[Any] = []


def setup_function():
    actions_log.clear()
    guard_log.clear()
    selector_log.clear()


# --- Tests ---


def test_parameters_passed_to_sync_action():
    def action(a: int, b: str, transition: Transition):
        actions_log.append((a, b, transition.trigger))

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B).on_entry(action)

    sm.fire(Trigger.X, 10, "hello")
    assert actions_log == [(10, "hello", Trigger.X)]


@pytest.mark.asyncio
async def test_parameters_passed_to_async_action():
    async def action(a: bool, transition: Transition, args: Sequence[Any]):
        # Test different ways of accepting args
        actions_log.append((a, transition.trigger, args))

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B).on_entry(action)

    await sm.fire_async(Trigger.X, True, 3.14, None)
    # Action wrapper passes (transition, all_args_tuple)
    # Action accepts `a` (True) and `transition`. `args` is not explicitly accepted.
    # The wrapper logic needs to be precise. Assuming wrapper passes what's accepted:
    # Let's redefine action to accept *args or specific types
    actions_log.clear()

    async def action_v2(a: bool, b: float, c: None, transition: Transition):
        actions_log.append((a, b, c, transition.trigger))

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B).on_entry(action_v2)
    await sm.fire_async(Trigger.X, True, 3.14, None)
    assert actions_log == [(True, 3.14, None, Trigger.X)]


def test_parameters_passed_to_sync_guard():
    def guard(x: int):
        guard_log.append(x)
        return x > 0

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard)

    sm.fire(Trigger.X, 10)
    assert guard_log == [10]
    assert sm.state == State.B

    with pytest.raises(InvalidTransitionError):
        sm.fire(Trigger.X, -5)
    assert guard_log == [10, -5]
    assert sm.state == State.B  # Still B from previous fire


@pytest.mark.asyncio
async def test_parameters_passed_to_async_guard():
    async def guard(name: str, value: int):
        guard_log.append((name, value))
        return value > 100

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard)

    await sm.fire_async(Trigger.X, "item", 200)
    assert guard_log == [("item", 200)]
    assert sm.state == State.B


def test_parameters_passed_to_sync_selector():
    def selector(target: str):
        selector_log.append(target)
        return State.B if target == "B" else State.A

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).dynamic(Trigger.X, selector)

    sm.fire(Trigger.X, "B")
    assert selector_log == ["B"]
    assert sm.state == State.B

    sm.fire(Trigger.X, "A")
    assert selector_log == ["B", "A"]
    assert sm.state == State.A


@pytest.mark.asyncio
async def test_parameters_passed_to_async_selector():
    async def selector(val: int):
        selector_log.append(val)
        return State.B if val > 0 else State.A

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).dynamic(Trigger.X, selector)

    await sm.fire_async(Trigger.X, 1)
    assert selector_log == [1]
    assert sm.state == State.B

    await sm.fire_async(Trigger.X, -1)
    assert selector_log == [1, -1]
    assert sm.state == State.A


def test_set_trigger_parameters_info():
    """Tests that set_trigger_parameters updates info."""
    sm = StateMachine[State, Trigger](State.A)
    sm.set_trigger_parameters(Trigger.X, int, str)
    sm.configure(State.A).permit(Trigger.X, State.B)

    info = sm.get_info()
    state_a_info = next(s for s in info.states if s.underlying_state == State.A)
    trans_x = state_a_info.fixed_transitions[0]
    assert trans_x.trigger.parameter_types == [int, str]
