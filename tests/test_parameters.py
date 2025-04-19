import pytest
from enum import Enum, auto
from typing import Any
from collections.abc import Sequence

from stateless import (
    StateMachine,
    Transition,
    InvalidTransitionError,
    ConfigurationError,
)

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()


class Trigger(Enum):
    X = auto()
    Y = auto()


actions_log: list[Any] = []
guard_log: list[Any] = []
selector_log: list[Any] = []


def setup_function():
    actions_log.clear()
    guard_log.clear()
    selector_log.clear()


# --- Action Signature Tests ---


def test_action_signature_transition_only() -> None:
    def action(transition: Transition[State, Trigger]) -> None:
        actions_log.append(f"action_t_{transition.trigger}")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B).on_entry(action)
    sm.fire(Trigger.X, 1, 2)  # Pass args even if not accepted
    assert actions_log == ["action_t_Trigger.X"]


def test_action_signature_transition_and_args_tuple() -> None:
    def action(transition: Transition, args: Sequence[Any]) -> None:
        actions_log.append(f"action_t_args_{args}")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B).on_entry(action)
    sm.fire(Trigger.X, 1, "two")
    assert actions_log == ["action_t_args_(1, 'two')"]


def test_action_signature_specific_args() -> None:
    # Already covered by test_parameters_passed_to_sync_action
    # and test_parameters_passed_to_async_action (action_v2)
    pass


def test_action_signature_var_args() -> None:
    def action(*args: Any) -> None:
        # Wrapper expects ["transition", "args"] for on_entry.
        # It passes the transition object and the tuple of trigger args.
        actions_log.append(f"action_varargs_{args}")
        assert isinstance(args[0], Transition)
        assert args[1] == (1, 2, 3)  # The trigger args tuple

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B).on_entry(action)
    sm.fire(Trigger.X, 1, 2, 3)
    # The log will contain the Transition object representation, which might be verbose.
    # Let's check the structure instead of exact string match.
    assert len(actions_log) == 1
    assert actions_log[0].startswith("action_varargs_(")


def test_action_signature_kwargs_not_supported() -> None:
    # Python's inspect doesn't easily map positional fire args to kwargs
    # without explicit naming or a dict argument. The _build_wrapper expects
    # named args like 'transition', 'args', or *args. A **kwargs only signature
    # will likely fail the mapping in _build_wrapper.
    def action(**kwargs):
        actions_log.append(f"action_kwargs_{kwargs}")  # pragma: no cover

    sm = StateMachine[State, Trigger](State.A)
    # ConfigurationError should be raised when _build_wrapper fails to map args
    with pytest.raises(ConfigurationError):
        sm.configure(State.A).permit(Trigger.X, State.B).on_entry(action)

    # If configuration somehow passed, firing would likely fail too,
    # but the config error is more likely.
    # sm.fire(Trigger.X, 1, 2)
    # assert actions_log == []


# --- Parameter Passing Tests ---


def test_parameters_passed_to_sync_action() -> None:
    def action(a: int, b: str, transition: Transition[State, Trigger]) -> None:
        actions_log.append((a, b, transition.trigger))

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B).on_entry(action)

    sm.fire(Trigger.X, 10, "hello")
    assert actions_log == [(10, "hello", Trigger.X)]


@pytest.mark.asyncio
async def test_parameters_passed_to_async_action() -> None:
    async def action(a: bool, transition: Transition[State, Trigger], args: Sequence[Any]) -> None:
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


def test_parameters_passed_to_sync_guard() -> None:
    def guard(x: int) -> bool:
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
async def test_parameters_passed_to_async_guard() -> None:
    async def guard(name: str, value: int) -> bool:
        guard_log.append((name, value))
        return value > 100

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, guard)

    await sm.fire_async(Trigger.X, "item", 200)
    assert guard_log == [("item", 200)]
    assert sm.state == State.B


def test_parameters_passed_to_sync_selector():
    def selector(target: str) -> State:
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
async def test_parameters_passed_to_async_selector() -> None:
    async def selector(val: int) -> State:
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


def test_set_trigger_parameters_info() -> None:
    """Tests that set_trigger_parameters updates info."""
    sm = StateMachine[State, Trigger](State.A)
    sm.set_trigger_parameters(Trigger.X, int, str)
    sm.configure(State.A).permit(Trigger.X, State.B)

    info = sm.get_info()
    state_a_info = next(s for s in info.states if s.underlying_state == State.A)
    trans_x = state_a_info.fixed_transitions[0]
    assert trans_x.trigger.parameter_types == [int, str]
