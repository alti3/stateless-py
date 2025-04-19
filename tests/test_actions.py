import pytest
from enum import Enum, auto
from typing import Any
from collections.abc import Sequence

from stateless import StateMachine, Transition

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()
    C = auto()


class Trigger(Enum):
    X = auto()
    Y = auto()
    Z = auto()  # For entry_from


actions_log: list[str] = []

# --- Sync Actions ---


def setup_function():
    """Clear log before each test."""
    actions_log.clear()


def sync_entry_a(t: Transition[State, Trigger]) -> None:
    actions_log.append(f"entry_A_from_{t.source}")


def sync_exit_a(t: Transition[State, Trigger]) -> None:
    actions_log.append(f"exit_A_to_{t.destination}")


def sync_activate_a() -> None:
    actions_log.append("activate_A")


def sync_deactivate_a() -> None:
    actions_log.append("deactivate_A")


def sync_entry_b(t: Transition[State, Trigger]) -> None:
    actions_log.append(f"entry_B_from_{t.source}")


def sync_exit_b(t: Transition[State, Trigger]) -> None:
    actions_log.append(f"exit_B_to_{t.destination}")


def sync_activate_b() -> None:
    actions_log.append("activate_B")


def sync_deactivate_b() -> None:
    actions_log.append("deactivate_B")


def test_entry_exit_actions_sync() -> None:
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_entry(sync_entry_a).on_exit(sync_exit_a).permit(
        Trigger.X, State.B
    )
    sm.configure(State.B).on_entry(sync_entry_b).on_exit(sync_exit_b).permit(
        Trigger.Y, State.A
    )

    # Initial state doesn't trigger entry actions in this implementation (matches C#?)
    # Let's assume initial state setup doesn't run on_entry/on_activate
    assert actions_log == []

    sm.fire(Trigger.X)  # A -> B
    assert sm.state == State.B
    # Order: Exit Source, Entry Destination
    assert actions_log == ["exit_A_to_State.B", "entry_B_from_State.A"]

    actions_log.clear()
    sm.fire(Trigger.Y)  # B -> A
    assert sm.state == State.A
    assert actions_log == ["exit_B_to_State.A", "entry_A_from_State.B"]


def test_activate_deactivate_actions_sync() -> None:
    # Activate/Deactivate primarily for substates, but test basic calls
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_activate(sync_activate_a).on_deactivate(
        sync_deactivate_a
    ).permit(Trigger.X, State.B)
    sm.configure(State.B).on_activate(sync_activate_b).on_deactivate(
        sync_deactivate_b
    ).permit(Trigger.Y, State.A)

    # Assume initial state activation happens implicitly if configured
    # This needs clarification based on desired behaviour or C# parity
    # For now, test transitions
    actions_log.clear()

    sm.fire(Trigger.X)  # A -> B
    assert sm.state == State.B
    # Order: Deactivate Source, Activate Destination (interleaved with exit/entry)
    # Expected based on StateRepresentation implementation: Deactivate A, Exit A, Entry B, Activate B
    assert actions_log == [
        "deactivate_A",
        "entry_B_from_State.A",
        "activate_B",
    ]  # Assuming no exit action configured here

    actions_log.clear()
    sm.fire(Trigger.Y)  # B -> A
    assert sm.state == State.A
    assert actions_log == ["deactivate_B", "entry_A_from_State.B", "activate_A"]


def test_on_entry_from_sync() -> None:
    """Tests actions executed only when entering from a specific trigger."""

    def entry_b_generic(t: Transition[State, Trigger]) -> None:
        actions_log.append("entry_B_generic")

    def entry_b_from_x(t: Transition[State, Trigger]) -> None:
        actions_log.append("entry_B_from_X")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.C).permit(Trigger.Y, State.B)  # Another way to enter B
    sm.configure(State.B).on_entry(entry_b_generic).on_entry_from(
        Trigger.X, entry_b_from_x
    )

    sm.fire(Trigger.X)  # A -> B via X
    assert sm.state == State.B
    # Both actions should run, order might depend on registration
    assert "entry_B_generic" in actions_log
    assert "entry_B_from_X" in actions_log
    assert len(actions_log) == 2

    # Transition from C to B via Y
    sm = StateMachine[State, Trigger](State.C)  # Reset SM
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.C).permit(Trigger.Y, State.B)
    sm.configure(State.B).on_entry(entry_b_generic).on_entry_from(
        Trigger.X, entry_b_from_x
    )
    actions_log.clear()

    sm.fire(Trigger.Y)  # C -> B via Y
    assert sm.state == State.B
    assert actions_log == ["entry_B_generic"]  # Only generic action runs


def test_sync_action_with_args() -> None:
    """Tests passing trigger arguments to sync actions."""
    entry_args = None

    def entry_b_action(transition: Transition[State, Trigger], args: Sequence[Any]) -> None:
        nonlocal entry_args
        entry_args = args
        actions_log.append(f"entry_B_args_{args}")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).on_entry(entry_b_action)

    sm.fire(Trigger.X, 10, "hello")
    assert sm.state == State.B
    assert entry_args == (10, "hello")
    assert actions_log == ["entry_B_args_(10, 'hello')"]


# --- Async Actions ---


async def async_entry_a(t: Transition[State, Trigger]) -> None:
    actions_log.append(f"async_entry_A_from_{t.source}")


async def async_exit_a(t: Transition[State, Trigger]) -> None:
    actions_log.append(f"async_exit_A_to_{t.destination}")


async def async_activate_a() -> None:
    actions_log.append("async_activate_A")


async def async_deactivate_a() -> None:
    actions_log.append("async_deactivate_A")


@pytest.mark.asyncio
async def test_entry_exit_actions_async() -> None:
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_entry(async_entry_a).on_exit(async_exit_a).permit(
        Trigger.X, State.B
    )
    sm.configure(State.B).permit(Trigger.Y, State.A)

    await sm.fire_async(Trigger.X)  # A -> B
    assert sm.state == State.B
    assert actions_log == [
        "async_exit_A_to_State.B",
        "async_entry_A_from_State.A",
    ]  # Assuming B has no entry action here

    actions_log.clear()
    sm.configure(State.B).on_entry(sync_entry_b)  # Add sync entry for B
    await sm.fire_async(Trigger.Y)  # B -> A
    assert sm.state == State.A
    # Order: Exit B (none), Entry A (async)
    assert actions_log == ["async_entry_A_from_State.B"]


@pytest.mark.asyncio
async def test_activate_deactivate_actions_async() -> None:
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_activate(async_activate_a).on_deactivate(
        async_deactivate_a
    ).permit(Trigger.X, State.B)
    sm.configure(State.B).permit(Trigger.Y, State.A)

    actions_log.clear()
    await sm.fire_async(Trigger.X)  # A -> B
    assert sm.state == State.B
    # Order: Deactivate A (async), Entry B (none), Activate B (none)
    assert actions_log == ["async_deactivate_A"]

    actions_log.clear()
    await sm.fire_async(Trigger.Y)  # B -> A
    assert sm.state == State.A
    # Order: Deactivate B (none), Entry A (none), Activate A (async)
    assert actions_log == ["async_activate_A"]


@pytest.mark.asyncio
async def test_on_entry_from_async() -> None:
    """Tests async actions executed only when entering from a specific trigger."""

    async def entry_b_generic(t: Transition[State, Trigger]) -> None:
        actions_log.append("async_entry_B_generic")

    async def entry_b_from_x(t: Transition[State, Trigger]) -> None:
        actions_log.append("async_entry_B_from_X")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).on_entry(entry_b_generic).on_entry_from(
        Trigger.X, entry_b_from_x
    )

    await sm.fire_async(Trigger.X)  # A -> B via X
    assert sm.state == State.B
    assert "async_entry_B_generic" in actions_log
    assert "async_entry_B_from_X" in actions_log


@pytest.mark.asyncio
async def test_async_action_with_args() -> None:
    """Tests passing trigger arguments to async actions."""
    entry_args = None

    async def entry_b_action(transition: Transition[State, Trigger], args: Sequence[Any]) -> None:
        nonlocal entry_args
        entry_args = args
        actions_log.append(f"async_entry_B_args_{args}")

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).on_entry(entry_b_action)

    await sm.fire_async(Trigger.X, True, 3.14)
    assert sm.state == State.B
    assert entry_args == (True, 3.14)
    assert actions_log == ["async_entry_B_args_(True, 3.14)"]


# --- Sync/Async Mismatch ---


def test_fire_sync_with_async_action_raises_type_error() -> None:
    """Tests that fire() raises TypeError if an async action is encountered."""

    async def entry_b(t):
        pass

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).on_entry(entry_b)  # Async entry action

    with pytest.raises(TypeError) as excinfo:
        sm.fire(Trigger.X)
    assert "synchronously" in str(excinfo.value)
    assert "Entry action" in str(excinfo.value) or "Activate action" in str(
        excinfo.value
    )  # Activate might also be checked


def test_fire_sync_with_async_exit_action_raises_type_error() -> None:
    """Tests that fire() raises TypeError if an async exit action is encountered."""

    async def exit_a(t):
        pass

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B).on_exit(
        exit_a
    )  # Async exit action
    sm.configure(State.B)

    with pytest.raises(TypeError) as excinfo:
        sm.fire(Trigger.X)
    assert "synchronously" in str(excinfo.value)
    assert "Exit action" in str(excinfo.value) or "Deactivate action" in str(
        excinfo.value
    )
