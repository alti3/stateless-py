import pytest
from enum import Enum, auto
from typing import Any

from stateless import StateMachine
from stateless.exceptions import ConfigurationError
# --- Test Setup ---


class Parent(Enum):
    A = auto()
    B = auto()
    C = auto()  # Top level


class ChildA(Enum):
    A1 = auto()
    A2 = auto()


class ChildB(Enum):
    B1 = auto()


class Trigger(Enum):
    GO_A1 = auto()
    GO_A2 = auto()
    GO_B1 = auto()
    GO_C = auto()
    INTERNAL_A = auto()
    EXIT_A = auto()


actions_log: list[str] = []


def setup_function():
    actions_log.clear()


def entry(state):
    return lambda t: actions_log.append(f"entry_{state.name}")


def exit_(state):
    return lambda t: actions_log.append(f"exit_{state.name}")


def activate(state):
    return lambda t: actions_log.append(f"activate_{state.name}")


def deactivate(state):
    return lambda t: actions_log.append(f"deactivate_{state.name}")


# --- Basic Hierarchy and Transitions ---


@pytest.mark.asyncio
async def test_substate_definition_and_is_in_state():
    sm = StateMachine[Any, Trigger](ChildA.A1)  # Start in substate
    sm.configure(ChildA.A1).substate_of(Parent.A)
    sm.configure(ChildA.A2).substate_of(Parent.A)
    sm.configure(Parent.B)  # Parent B exists
    sm.configure(Parent.A)  # Parent A exists

    assert sm.state == ChildA.A1
    assert sm.is_in_state(ChildA.A1) is True
    assert sm.is_in_state(Parent.A) is True  # Should be true if in substate
    assert sm.is_in_state(ChildA.A2) is False
    assert sm.is_in_state(Parent.B) is False


@pytest.mark.asyncio
async def test_transition_between_substates():
    sm = StateMachine[Any, Trigger](ChildA.A1)
    sm.configure(ChildA.A1).substate_of(Parent.A).permit(Trigger.GO_A2, ChildA.A2)
    sm.configure(ChildA.A2).substate_of(Parent.A).permit(Trigger.GO_A1, ChildA.A1)
    sm.configure(Parent.A)  # Define parent

    await sm.fire_async(Trigger.GO_A2)
    assert sm.state == ChildA.A2
    assert sm.is_in_state(Parent.A) is True

    await sm.fire_async(Trigger.GO_A1)
    assert sm.state == ChildA.A1
    assert sm.is_in_state(Parent.A) is True


@pytest.mark.asyncio
async def test_transition_from_substate_to_different_parent():
    sm = StateMachine[Any, Trigger](ChildA.A1)
    sm.configure(ChildA.A1).substate_of(Parent.A).permit(Trigger.GO_B1, ChildB.B1)
    sm.configure(ChildB.B1).substate_of(Parent.B)
    sm.configure(Parent.A)
    sm.configure(Parent.B)

    assert sm.is_in_state(Parent.A) is True
    assert sm.is_in_state(Parent.B) is False

    await sm.fire_async(Trigger.GO_B1)
    assert sm.state == ChildB.B1
    assert sm.is_in_state(Parent.A) is False
    assert sm.is_in_state(Parent.B) is True


@pytest.mark.asyncio
async def test_transition_from_substate_to_superstate():
    sm = StateMachine[Any, Trigger](ChildA.A1)
    sm.configure(ChildA.A1).substate_of(Parent.A).permit(
        Trigger.EXIT_A, Parent.B
    )  # Go to sibling parent
    sm.configure(Parent.A)
    sm.configure(Parent.B)

    await sm.fire_async(Trigger.EXIT_A)
    assert sm.state == Parent.B
    assert sm.is_in_state(Parent.A) is False


@pytest.mark.asyncio
async def test_transition_from_superstate_to_substate():
    sm = StateMachine[Any, Trigger](Parent.B)
    sm.configure(Parent.B).permit(Trigger.GO_A1, ChildA.A1)
    sm.configure(ChildA.A1).substate_of(Parent.A)
    sm.configure(Parent.A)

    await sm.fire_async(Trigger.GO_A1)
    assert sm.state == ChildA.A1
    assert sm.is_in_state(Parent.A) is True


@pytest.mark.asyncio
async def test_unhandled_trigger_in_substate_handled_by_superstate():
    sm = StateMachine[Any, Trigger](ChildA.A1)
    sm.configure(ChildA.A1).substate_of(Parent.A)  # No triggers defined for A1
    sm.configure(Parent.A).permit(Trigger.GO_C, Parent.C)  # Parent handles GO_C
    sm.configure(Parent.C)

    await sm.fire_async(Trigger.GO_C)
    assert sm.state == Parent.C


# --- Action Execution Order ---


@pytest.mark.asyncio
async def test_substate_action_order_full():
    """Tests entry/exit and activate/deactivate order during transitions."""
    sm = StateMachine[Any, Trigger](Parent.C)  # Start outside hierarchy
    sm.configure(Parent.C).permit(Trigger.GO_A1, ChildA.A1)

    sm.configure(ChildA.A1).substate_of(Parent.A)\
        .on_entry(entry(ChildA.A1))\
        .on_exit(exit_(ChildA.A1))\
        .on_activate(activate(ChildA.A1))\
        .on_deactivate(deactivate(ChildA.A1))\
        .permit(Trigger.GO_B1, ChildB.B1)

    sm.configure(Parent.A)\
        .on_entry(entry(Parent.A))\
        .on_exit(exit_(Parent.A))\
        .on_activate(activate(Parent.A))\
        .on_deactivate(deactivate(Parent.A))

    sm.configure(ChildB.B1).substate_of(Parent.B)\
        .on_entry(entry(ChildB.B1))\
        .on_activate(activate(ChildB.B1))
        # No exit/deactivate needed for this test path

    sm.configure(Parent.B)\
        .on_entry(entry(Parent.B))\
        .on_activate(activate(Parent.B))
        # No exit/deactivate needed for this test path

    # Transition C -> A1 (enters A, then A1; activates A, then A1)
    await sm.fire_async(Trigger.GO_A1)
    assert sm.state == ChildA.A1
    # Order: Entry Super -> Entry Sub -> Activate Super -> Activate Sub
    assert actions_log == [
        "entry_Parent.A",
        "entry_ChildA.A1",
        "activate_Parent.A",
        "activate_ChildA.A1",
    ]

    actions_log.clear()
    # Transition A1 -> B1
    # Exit/Deactivate Order: Deactivate Sub -> Deactivate Super -> Exit Sub -> Exit Super
    # Entry/Activate Order: Entry Super -> Entry Sub -> Activate Super -> Activate Sub
    await sm.fire_async(Trigger.GO_B1)
    assert sm.state == ChildB.B1
    assert actions_log == [
        "deactivate_ChildA.A1",
        "deactivate_Parent.A",
        "exit_ChildA.A1",
        "exit_Parent.A",
        "entry_Parent.B",
        "entry_ChildB.B1",
        "activate_Parent.B",
        "activate_ChildB.B1",
    ]


@pytest.mark.asyncio
async def test_substate_action_order_enter_exit():
    # This test is now covered by test_substate_action_order_full
    # We can keep it if we want a simpler version focusing only on entry/exit
    # Or remove it. Let's keep it for now but note the overlap.
    sm = StateMachine[Any, Trigger](Parent.C)  # Start outside hierarchy
    sm.configure(Parent.C).permit(Trigger.GO_A1, ChildA.A1)
    sm.configure(ChildA.A1).substate_of(Parent.A).on_entry(entry(ChildA.A1)).on_exit(
        exit_(ChildA.A1)
    ).permit(Trigger.GO_B1, ChildB.B1)
    sm.configure(Parent.A).on_entry(entry(Parent.A)).on_exit(exit_(Parent.A))
    sm.configure(ChildB.B1).substate_of(Parent.B).on_entry(entry(ChildB.B1))
    sm.configure(Parent.B).on_entry(entry(Parent.B))

    # Transition C -> A1 (enters A, then A1)
    await sm.fire_async(Trigger.GO_A1)
    assert sm.state == ChildA.A1
    # Entry order: Superstate -> Substate
    assert actions_log == ["entry_Parent.A", "entry_ChildA.A1"]

    actions_log.clear()
    # Transition A1 -> B1 (exits A1, then A; enters B, then B1)
    await sm.fire_async(Trigger.GO_B1)
    assert sm.state == ChildB.B1
    # Exit order: Substate -> Superstate; Entry order: Superstate -> Substate
    assert actions_log == [
        "exit_ChildA.A1",
        "exit_Parent.A",
        "entry_Parent.B",
        "entry_ChildB.B1",
    ]


# --- Initial Transition ---


@pytest.mark.asyncio
async def test_initial_transition_to_substate():
    sm = StateMachine[Any, Trigger](Parent.C)  # Start outside
    sm.configure(Parent.C).permit(Trigger.GO_A1, Parent.A)  # Target Parent A

    sm.configure(Parent.A).initial_transition(ChildA.A1).on_entry(entry(Parent.A))
    sm.configure(ChildA.A1).substate_of(Parent.A).on_entry(entry(ChildA.A1))
    sm.configure(ChildA.A2).substate_of(Parent.A).on_entry(entry(ChildA.A2))

    await sm.fire_async(Trigger.GO_A1)
    # Should enter Parent.A, then immediately transition to and enter ChildA.A1
    assert sm.state == ChildA.A1
    assert actions_log == ["entry_Parent.A", "entry_ChildA.A1"]


@pytest.mark.asyncio
async def test_initial_transition_to_nested_substate():
    class GrandChildA1(Enum):
        G1 = auto()

    sm = StateMachine[Any, Trigger](Parent.C)
    sm.configure(Parent.C).permit(Trigger.GO_A1, Parent.A)

    sm.configure(Parent.A).initial_transition(ChildA.A1).on_entry(entry(Parent.A))
    sm.configure(ChildA.A1).substate_of(Parent.A).initial_transition(
        GrandChildA1.G1
    ).on_entry(entry(ChildA.A1))
    sm.configure(GrandChildA1.G1).substate_of(ChildA.A1).on_entry(
        entry(GrandChildA1.G1)
    )

    await sm.fire_async(Trigger.GO_A1)
    assert sm.state == GrandChildA1.G1
    assert actions_log == ["entry_Parent.A", "entry_ChildA.A1", "entry_GrandChildA1.G1"]


def test_initial_transition_target_not_substate_error():
    sm = StateMachine[Any, Trigger](Parent.C)
    with pytest.raises(ConfigurationError) as excinfo:
        sm.configure(Parent.A).initial_transition(Parent.B)  # B is not a substate of A
    assert "must be a substate of" in str(excinfo.value)
