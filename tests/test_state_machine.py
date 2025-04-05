import pytest
from enum import Enum, auto
import asyncio
import time
from unittest.mock import MagicMock, Mock

from stateless import StateMachine, InvalidTransitionError
from stateless.exceptions import UnhandledTriggerError
from stateless.firing_modes import FiringMode
from stateless.state import State
from stateless.transition import Transition

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
    unhandled_log: list[str] = []

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
    unhandled_log: list[str] = []

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
    unhandled_log: list[str] = []

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


def test_state_accessor_raises_exception():
    """Tests when the state accessor raises an error."""
    def getter_error():
        raise ValueError("Cannot get state")
    def setter(s): pass # pragma: no cover

    # Error during initialization (accessor called after internal state set)
    with pytest.raises(ValueError, match="Cannot get state"):
        StateMachine[State, Trigger](
            State.A, state_accessor=getter_error, state_mutator=setter
        )

    # Error during firing (accessor called before finding handler)
    external_state = {"current": State.A}
    getter_calls = 0
    def getter_error_later():
        nonlocal getter_calls
        getter_calls += 1
        if getter_calls > 1: # Error on second call (during fire)
            raise ValueError("Cannot get state later")
        return external_state["current"]
    def setter_ok(s): external_state["current"] = s # pragma: no cover

    sm = StateMachine[State, Trigger](
        State.A, state_accessor=getter_error_later, state_mutator=setter_ok
    )
    sm.configure(State.A).permit(Trigger.X, State.B)

    # The call to sm.state within sm.fire() will trigger the error
    with pytest.raises(ValueError, match="Cannot get state later"):
        sm.fire(Trigger.X)
    # State should not have changed as error occurred before transition logic
    assert external_state["current"] == State.A
    # Internal state also shouldn't change if accessor fails early
    # assert sm._current_state == State.A # Cannot access internal state directly


def test_state_mutator_raises_exception():
    """Tests when the state mutator raises an error."""
    external_state = {"current": State.A}
    def getter(): return external_state["current"]
    def setter_error(s):
        # Simulate failure during state update
        raise ValueError("Cannot set state")

    sm = StateMachine[State, Trigger](
        State.A, state_accessor=getter, state_mutator=setter_error
    )
    sm.configure(State.A).permit(Trigger.X, State.B)

    with pytest.raises(ValueError, match="Cannot set state"):
        sm.fire(Trigger.X)

    # Check that external state wasn't updated
    assert external_state["current"] == State.A
    # Check that internal state (via accessor) also reflects the original state,
    # as the mutator failed before the conceptual state change completed.
    assert sm.state == State.A


def test_initial_state_vs_accessor_mismatch():
    """Tests behavior when constructor initial_state differs from accessor."""
    external_state = {"current": State.B} # Accessor returns B
    def getter(): return external_state["current"]
    def setter(s): external_state["current"] = s

    # Initialize with A, but accessor returns B
    sm = StateMachine[State, Trigger](
        State.A, state_accessor=getter, state_mutator=setter
    )

    # What is the expected state? C# likely uses the accessor's value.
    assert sm.state == State.B # Assert that accessor value takes precedence
    assert external_state["current"] == State.B


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


# --- Transition Completed Callback Tests ---

def test_sync_transition_completed_callback() -> None:
    # Arrange
    class TestState(Enum):
        A = auto()
        B = auto()

    class TestTrigger(Enum):
        X = auto()

    execution_order: list[str] = []
    transition_info: list[Transition] = []

    def on_exit_a(t):
        execution_order.append("exit_a")

    def on_entry_b(t):
        execution_order.append("entry_b")

    def on_completed(t):
        execution_order.append("completed")
        transition_info.append(t)

    sm = StateMachine(
        TestState.A, on_transition_completed_callback=on_completed
    )
    sm.configure(TestState.A).permit(TestTrigger.X, TestState.B).on_exit(on_exit_a)
    sm.configure(TestState.B).on_entry(on_entry_b)

    # Act
    sm.fire(TestTrigger.X)

    # Assert
    assert sm.state == TestState.B
    assert execution_order == ["exit_a", "entry_b", "completed"]
    assert len(transition_info) == 1
    t = transition_info[0]
    assert t.source == TestState.A
    assert t.destination == TestState.B
    assert t.trigger == TestTrigger.X
    assert t.args == ()


@pytest.mark.asyncio
async def test_async_transition_completed_callback() -> None:
    # Arrange
    class TestState(Enum):
        A = auto()
        B = auto()

    class TestTrigger(Enum):
        X = auto()

    execution_order: list[str] = []
    transition_info: list[Transition] = []

    async def on_exit_a(t):
        await asyncio.sleep(0.01)
        execution_order.append("exit_a")

    async def on_entry_b(t):
        await asyncio.sleep(0.01)
        execution_order.append("entry_b")

    async def on_completed_async(t):
        await asyncio.sleep(0.01)
        execution_order.append("completed_async")
        transition_info.append(t)

    sm = StateMachine(
        TestState.A, on_transition_completed_async_callback=on_completed_async
    )
    sm.configure(TestState.A).permit(TestTrigger.X, TestState.B).on_exit(on_exit_a)
    sm.configure(TestState.B).on_entry(on_entry_b)

    # Act
    await sm.fire_async(TestTrigger.X)

    # Assert
    assert sm.state == TestState.B
    assert execution_order == ["exit_a", "entry_b", "completed_async"]
    assert len(transition_info) == 1
    t = transition_info[0]
    assert t.source == TestState.A
    assert t.destination == TestState.B
    assert t.trigger == TestTrigger.X
    assert t.args == ()


@pytest.mark.asyncio
async def test_both_transition_completed_callbacks_async_fire() -> None:
    # Arrange
    class TestState(Enum):
        A = auto()
        B = auto()

    class TestTrigger(Enum):
        X = auto()

    execution_order: list[str] = []
    transition_info_sync: list[Transition] = []
    transition_info_async: list[Transition] = []

    async def on_exit_a(t):
        execution_order.append("exit_a")

    async def on_entry_b(t):
        execution_order.append("entry_b")

    def on_completed_sync(t):
        execution_order.append("completed_sync")
        transition_info_sync.append(t)

    async def on_completed_async(t):
        execution_order.append("completed_async")
        transition_info_async.append(t)

    sm = StateMachine(
        TestState.A,
        on_transition_completed_callback=on_completed_sync,
        on_transition_completed_async_callback=on_completed_async,
    )
    sm.configure(TestState.A).permit(TestTrigger.X, TestState.B).on_exit(on_exit_a)
    sm.configure(TestState.B).on_entry(on_entry_b)

    # Act
    await sm.fire_async(TestTrigger.X, 1, "arg2")

    # Assert
    assert sm.state == TestState.B
    # Sync callback runs first in the final step
    assert execution_order == ["exit_a", "entry_b", "completed_sync", "completed_async"]
    assert len(transition_info_sync) == 1
    assert len(transition_info_async) == 1
    t_sync = transition_info_sync[0]
    t_async = transition_info_async[0]
    assert t_sync is t_async # Should be the same transition object
    assert t_sync.source == TestState.A
    assert t_sync.destination == TestState.B
    assert t_sync.trigger == TestTrigger.X
    assert t_sync.args == (1, "arg2")


def test_sync_transition_completed_internal_transition() -> None:
    # Arrange
    class TestState(Enum): A = auto()
    class TestTrigger(Enum): X = auto()

    execution_order: list[str] = []
    transition_info: list[Transition] = []

    def internal_action(t):
        execution_order.append("internal_action")

    def on_completed(t):
        execution_order.append("completed")
        transition_info.append(t)

    sm = StateMachine(
        TestState.A, on_transition_completed_callback=on_completed
    )
    sm.configure(TestState.A).internal_transition(TestTrigger.X, internal_action)

    # Act
    sm.fire(TestTrigger.X, "param")

    # Assert
    assert sm.state == TestState.A # State doesn't change
    assert execution_order == ["internal_action", "completed"]
    assert len(transition_info) == 1
    t = transition_info[0]
    assert t.source == TestState.A
    assert t.destination == TestState.A # Destination is same as source for internal
    assert t.trigger == TestTrigger.X
    assert t.args == ("param",)


@pytest.mark.asyncio
async def test_async_transition_completed_reentry_transition() -> None:
    # Arrange
    class TestState(Enum): A = auto()
    class TestTrigger(Enum): X = auto()

    execution_order: list[str] = []
    transition_info: list[Transition] = []

    async def on_exit_a(t):
        execution_order.append("exit_a")

    async def on_entry_a(t):
        execution_order.append("entry_a")

    async def on_completed_async(t):
        execution_order.append("completed_async")
        transition_info.append(t)

    sm = StateMachine(
        TestState.A, on_transition_completed_async_callback=on_completed_async
    )
    sm.configure(TestState.A).permit_reentry(TestTrigger.X).on_exit(on_exit_a).on_entry(on_entry_a)

    # Act
    await sm.fire_async(TestTrigger.X)

    # Assert
    assert sm.state == TestState.A
    assert execution_order == ["exit_a", "entry_a", "completed_async"]
    assert len(transition_info) == 1
    t = transition_info[0]
    assert t.source == TestState.A
    assert t.destination == TestState.A # Destination is same as source for reentry
    assert t.trigger == TestTrigger.X
    assert t.args == ()

@pytest.mark.asyncio
async def test_async_transition_completed_queued_mode() -> None:
    # Arrange
    class TestState(Enum):
        A = auto()
        B = auto()
    class TestTrigger(Enum):
        X = auto()

    execution_order: list[str] = []
    transition_info: list[Transition] = []
    loop = asyncio.get_running_loop()

    async def on_exit_a(t):
        await asyncio.sleep(0.01)
        execution_order.append("exit_a")

    async def on_entry_b(t):
        await asyncio.sleep(0.01)
        execution_order.append("entry_b")

    async def on_completed_async(t):
        await asyncio.sleep(0.01)
        execution_order.append("completed_async")
        transition_info.append(t)
        # Add a small delay after completion callback finishes
        await asyncio.sleep(0.01)


    sm = StateMachine(
        TestState.A,
        firing_mode=FiringMode.QUEUED,
        on_transition_completed_async_callback=on_completed_async,
    )
    sm.configure(TestState.A).permit(TestTrigger.X, TestState.B).on_exit(on_exit_a)
    sm.configure(TestState.B).on_entry(on_entry_b)

    # Act
    # Explicitly start if not auto-started (depends on loop state during init)
    await sm.start()
    fire_task = loop.create_task(sm.fire_async(TestTrigger.X))

    # Allow time for the queue processor to pick up and process the item
    # Wait significantly longer than the combined action/callback delays
    await asyncio.wait_for(sm._queued_triggers.join(), timeout=0.5) # Wait for queue to empty
    await asyncio.sleep(0.1) # Allow callbacks to finish after join

    # Assert
    assert sm.state == TestState.B
    assert execution_order == ["exit_a", "entry_b", "completed_async"]
    assert len(transition_info) == 1
    t = transition_info[0]
    assert t.source == TestState.A
    assert t.destination == TestState.B
    assert t.trigger == TestTrigger.X
    assert t.args == ()

    # Cleanup
    await sm.stop()
    # Ensure fire task completed (should have already)
    await asyncio.wait_for(fire_task, timeout=0.1)


# Add more placeholder tests or basic structure
# def test_simple_transition(): ...
# def test_unconfigured_trigger(): ...
# def test_state_accessor_mutator(): ...
