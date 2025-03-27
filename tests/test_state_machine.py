import pytest
from enum import Enum, auto
from typing import List

from stateless import StateMachine, StateT, TriggerT, InvalidTransitionError, FiringMode

# TODO: Add actual tests for StateMachine core functionality


class State(Enum):
    A = auto()
    B = auto()
    C = auto()


class Trigger(Enum):
    X = auto()
    Y = auto()
    Z = auto()  # Unconfigured trigger


def test_initial_state():
    """Tests if the state machine initializes to the correct state."""
    sm = StateMachine[State, Trigger](State.A)
    assert sm.state == State.A


def test_simple_transition():
    """Tests a basic transition using permit."""
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).permit(Trigger.Y, State.C)

    assert sm.state == State.A
    sm.fire(Trigger.X)
    assert sm.state == State.B
    sm.fire(Trigger.Y)
    assert sm.state == State.C


@pytest.mark.asyncio
async def test_simple_transition_async():
    """Tests a basic transition using fire_async."""
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)

    assert sm.state == State.A
    await sm.fire_async(Trigger.X)
    assert sm.state == State.B


def test_unconfigured_trigger_raises_error():
    """Tests that firing an unconfigured trigger raises InvalidTransitionError."""
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)

    with pytest.raises(InvalidTransitionError) as excinfo:
        sm.fire(Trigger.Z)  # Z is not configured for state A
    assert "No valid transitions permitted" in str(excinfo.value)
    assert "Trigger.Z" in str(excinfo.value)
    assert "State.A" in str(excinfo.value)


@pytest.mark.asyncio
async def test_unconfigured_trigger_raises_error_async():
    """Tests unconfigured trigger with fire_async."""
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)

    with pytest.raises(InvalidTransitionError):
        await sm.fire_async(Trigger.Z)


def test_trigger_configured_for_different_state_raises_error():
    """Tests firing a trigger valid only in another state."""
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).permit(Trigger.Y, State.C)  # Y only valid in B

    assert sm.state == State.A
    with pytest.raises(InvalidTransitionError):
        sm.fire(Trigger.Y)  # Cannot fire Y from state A


# --- Unhandled Trigger Handler ---


def test_unhandled_trigger_sync_handler():
    """Tests the synchronous unhandled trigger handler."""
    unhandled_log: List[str] = []

    def handler(state, trigger, args):
        unhandled_log.append(f"Unhandled: {state=}, {trigger=}, {args=}")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.on_unhandled_trigger(handler)

    sm.fire(Trigger.Z, 1, "two")  # Fire unhandled trigger

    assert sm.state == State.A  # State should not change
    assert len(unhandled_log) == 1
    assert "state=State.A" in unhandled_log[0]
    assert "trigger=Trigger.Z" in unhandled_log[0]
    assert "args=(1, 'two')" in unhandled_log[0]


@pytest.mark.asyncio
async def test_unhandled_trigger_async_handler():
    """Tests the asynchronous unhandled trigger handler."""
    unhandled_log: List[str] = []

    async def handler(state, trigger, args):
        unhandled_log.append(f"Unhandled: {state=}, {trigger=}, {args=}")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.on_unhandled_trigger_async(handler)

    await sm.fire_async(Trigger.Z, "arg")

    assert sm.state == State.A
    assert len(unhandled_log) == 1
    assert "state=State.A" in unhandled_log[0]
    assert "trigger=Trigger.Z" in unhandled_log[0]
    assert "args=('arg',)" in unhandled_log[0]


@pytest.mark.asyncio
async def test_unhandled_trigger_sync_handler_called_by_async():
    """Tests calling a sync unhandled handler via fire_async."""
    unhandled_log: List[str] = []

    def handler(state, trigger, args):
        unhandled_log.append("Sync handler called")

    sm = StateMachine[State, Trigger](State.A)
    sm.on_unhandled_trigger(handler)  # Register sync handler

    await sm.fire_async(Trigger.Z)  # Fire async

    assert sm.state == State.A
    assert unhandled_log == ["Sync handler called"]


def test_unhandled_trigger_async_handler_raises_sync():
    """Tests that fire() raises TypeError if async unhandled handler exists."""

    async def handler(state, trigger, args):
        pass

    sm = StateMachine[State, Trigger](State.A)
    sm.on_unhandled_trigger_async(handler)

    with pytest.raises(TypeError) as excinfo:
        sm.fire(Trigger.Z)
    assert "Configured handler is async" in str(excinfo.value)


# --- State Accessor/Mutator ---


def test_state_accessor_mutator():
    """Tests using external state via accessor/mutator."""
    external_state = {"current": State.A}

    def getter():
        return external_state["current"]

    def setter(new_state):
        external_state["current"] = new_state

    sm = StateMachine[State, Trigger](
        State.A, state_accessor=getter, state_mutator=setter
    )
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).permit(Trigger.Y, State.A)

    assert sm.state == State.A
    assert external_state["current"] == State.A

    sm.fire(Trigger.X)
    assert sm.state == State.B
    assert external_state["current"] == State.B

    sm.fire(Trigger.Y)
    assert sm.state == State.A
    assert external_state["current"] == State.A


# --- Sync Reentrancy Check ---
def test_sync_reentrant_fire_raises_error():
    """Tests that immediate synchronous reentrant firing raises an error."""
    sm = StateMachine[State, Trigger](State.A)

    def action_that_fires():
        print("Action trying to fire Trigger.Y")
        sm.fire(Trigger.Y)  # Reentrant fire

    sm.configure(State.A).permit(Trigger.X, State.B).on_exit(action_that_fires)
    sm.configure(State.B).permit(Trigger.Y, State.A)  # Need Y configured somewhere

    with pytest.raises(InvalidTransitionError) as excinfo:
        sm.fire(Trigger.X)
    assert "Reentrant call to 'fire' detected" in str(excinfo.value)


# --- can_fire / get_permitted_triggers (Sync) ---


def test_can_fire_sync_success():
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    assert sm.can_fire(Trigger.X) is True


def test_can_fire_sync_fail_wrong_state():
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.B).permit(Trigger.X, State.C)
    assert sm.can_fire(Trigger.X) is False


def test_can_fire_sync_fail_unconfigured():
    sm = StateMachine[State, Trigger](State.A)
    assert sm.can_fire(Trigger.X) is False


def test_get_permitted_triggers_sync():
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.A).permit(Trigger.Y, State.C)
    sm.configure(State.B).permit(Trigger.Z, State.A)  # Z not permitted in A

    permitted = sm.get_permitted_triggers()
    assert set(permitted) == {Trigger.X, Trigger.Y}


def test_get_permitted_triggers_sync_empty():
    sm = StateMachine[State, Trigger](State.A)
    # No transitions configured for A
    sm.configure(State.B).permit(Trigger.X, State.A)
    assert sm.get_permitted_triggers() == []


# Add more placeholder tests or basic structure
# def test_simple_transition(): ...
# def test_unconfigured_trigger(): ...
# def test_state_accessor_mutator(): ...
