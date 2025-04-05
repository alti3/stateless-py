import pytest
from enum import Enum, auto
from typing import Any
from collections.abc import Sequence
import asyncio

from stateless import StateMachine, Transition, InvalidTransitionError


class State(Enum):
    A = auto()
    B = auto()


class Trigger(Enum):
    INTERNAL = auto()
    MOVE = auto()


@pytest.mark.asyncio
async def test_internal_transition_executes_action():
    """Tests that an internal transition executes its action."""
    actions_executed: list[str] = []

    def internal_action(transition: Transition[State, Trigger], args: Sequence[Any]):
        actions_executed.append(f"internal_action_{args[0]}")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).internal_transition(Trigger.INTERNAL, internal_action)
    sm.configure(State.A).permit(Trigger.MOVE, State.B)

    assert sm.state == State.A
    await sm.fire_async(Trigger.INTERNAL, "arg1")

    assert sm.state == State.A  # State should not change
    assert actions_executed == ["internal_action_arg1"]


@pytest.mark.asyncio
async def test_internal_transition_multiple_args():
    """Tests internal transition action receiving multiple arguments."""
    action_args = None

    def internal_action(transition: Transition, args: Sequence[Any]):
        nonlocal action_args
        action_args = args

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).internal_transition(Trigger.INTERNAL, internal_action)

    await sm.fire_async(Trigger.INTERNAL, 100, "test", True)
    assert sm.state == State.A
    assert action_args == (100, "test", True)


@pytest.mark.asyncio
async def test_internal_transition_specific_args():
    """Tests internal transition action receiving specific typed arguments."""
    action_args = None

    def internal_action(val: int, name: str):
        nonlocal action_args
        action_args = (val, name)

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).internal_transition(Trigger.INTERNAL, internal_action)

    await sm.fire_async(Trigger.INTERNAL, 99, "specific")
    assert sm.state == State.A
    assert action_args == (99, "specific")


@pytest.mark.asyncio
async def test_internal_transition_does_not_exit_enter():
    """Tests that internal transitions don't trigger exit/entry actions."""
    actions_executed: list[str] = []

    def internal_action():
        actions_executed.append("internal")

    def entry_a(t):
        actions_executed.append("entry_a")

    def exit_a(t):
        actions_executed.append("exit_a")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_entry(entry_a).on_exit(exit_a).internal_transition(
        Trigger.INTERNAL, internal_action
    ).permit(Trigger.MOVE, State.B)

    actions_executed.clear()  # Clear potential initial entry action if run
    await sm.fire_async(Trigger.INTERNAL)

    assert sm.state == State.A
    assert actions_executed == ["internal"]  # Only internal action should run


@pytest.mark.asyncio
async def test_internal_transition_with_guards():
    """Tests guards on internal transitions."""
    actions_executed: list[str] = []
    can_run = False

    def internal_action():
        actions_executed.append("internal")

    def guard():
        return can_run

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).internal_transition(
        Trigger.INTERNAL, internal_action, guard=guard
    )

    # Try when guard is false
    with pytest.raises(InvalidTransitionError):  # Expect guard failure
        await sm.fire_async(Trigger.INTERNAL)
    assert actions_executed == []
    assert sm.state == State.A

    # Try when guard is true
    can_run = True
    await sm.fire_async(Trigger.INTERNAL)
    assert actions_executed == ["internal"]
    assert sm.state == State.A


@pytest.mark.asyncio
async def test_internal_transition_async_action():
    """Tests an internal transition with an async action."""
    actions_executed: list[str] = []

    async def internal_action_async():
        await asyncio.sleep(0.01)
        actions_executed.append("internal_async")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).internal_transition(Trigger.INTERNAL, internal_action_async)

    await sm.fire_async(Trigger.INTERNAL)
    assert sm.state == State.A
    assert actions_executed == ["internal_async"]


def test_fire_sync_with_async_internal_action_raises_type_error():
    """Tests that fire() raises TypeError for async internal action."""
    actions_executed: list[str] = []

    async def internal_action_async():
        actions_executed.append("internal_async")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).internal_transition(Trigger.INTERNAL, internal_action_async)

    with pytest.raises(TypeError) as excinfo:
        sm.fire(Trigger.INTERNAL)
    assert "synchronously" in str(excinfo.value)
    assert "Internal action" in str(excinfo.value)
    assert actions_executed == []  # Action should not run


# TODO: Add tests for async internal actions, sync firing with async internal action (TypeError)
