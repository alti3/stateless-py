from enum import Enum, auto
from typing import Any

from stateless import StateMachine
from stateless.reflection import (
    StateMachineInfo,
    StateInfo,
)
from stateless.transition import Transition

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()
    C = auto()


class SubA(Enum):
    A1 = auto()
    A2 = auto()


class Trigger(Enum):
    X = auto()
    Y = auto()
    Z = auto()
    IG = auto()
    DYN = auto()
    INT = auto()


def guard_always_true() -> bool:
    return True


async def guard_async() -> bool:
    return True


def action_sync(t: Transition[State, Trigger]) -> None:
    pass


async def action_async(t: Transition[State, Trigger]) -> None:
    pass


def selector_sync() -> State:
    return State.C


# --- Tests ---


def test_get_info_simple_machine() -> None:
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).permit(Trigger.Y, State.A)

    info = sm.get_info()

    assert isinstance(info, StateMachineInfo)
    assert info.initial_state == State.A
    assert info.state_type == State
    assert info.trigger_type == Trigger
    assert len(info.states) == 2

    state_a_info = next(s for s in info.states if s.underlying_state == State.A)
    state_b_info = next(s for s in info.states if s.underlying_state == State.B)

    assert isinstance(state_a_info, StateInfo)
    assert len(state_a_info.fixed_transitions) == 1
    assert state_a_info.fixed_transitions[0].trigger.underlying_trigger == Trigger.X
    assert state_a_info.fixed_transitions[0].destination_state == State.B
    assert state_a_info.fixed_transitions[0].guard_conditions == []

    assert len(state_b_info.fixed_transitions) == 1
    assert state_b_info.fixed_transitions[0].trigger.underlying_trigger == Trigger.Y
    assert state_b_info.fixed_transitions[0].destination_state == State.A


def test_get_info_with_guards_actions() -> None:
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_entry(action_sync, "Entry A").on_exit(
        action_async
    ).permit_if(Trigger.X, State.B, guard_always_true, "Guard X")

    info = sm.get_info()
    state_a_info = next(s for s in info.states if s.underlying_state == State.A)

    assert len(state_a_info.entry_actions) == 1
    assert state_a_info.entry_actions[0].method_description.description == "Entry A"
    assert state_a_info.entry_actions[0].method_description.is_async is False

    assert len(state_a_info.exit_actions) == 1
    assert state_a_info.exit_actions[0].method_description.method_name == "action_async"
    assert state_a_info.exit_actions[0].method_description.is_async is True

    assert len(state_a_info.fixed_transitions) == 1
    trans_x = state_a_info.fixed_transitions[0]
    assert trans_x.trigger.underlying_trigger == Trigger.X
    assert len(trans_x.guard_conditions) == 1
    assert trans_x.guard_conditions[0].method_description.description == "Guard X"
    assert trans_x.guard_conditions[0].method_description.is_async is False


def test_get_info_substates() -> None:
    sm = StateMachine[Any, Trigger](SubA.A1)
    sm.configure(SubA.A1).substate_of(State.A).permit(Trigger.X, SubA.A2)
    sm.configure(SubA.A2).substate_of(State.A).permit(Trigger.Y, State.B)
    sm.configure(State.A).on_activate(action_sync)
    sm.configure(State.B)

    info = sm.get_info()
    assert len(info.states) == 4  # A, B, A1, A2

    state_a_info = next(s for s in info.states if s.underlying_state == State.A)
    state_a1_info = next(s for s in info.states if s.underlying_state == SubA.A1)
    state_a2_info = next(s for s in info.states if s.underlying_state == SubA.A2)

    assert len(state_a_info.substates) == 2
    assert state_a1_info in state_a_info.substates
    assert state_a2_info in state_a_info.substates
    assert state_a1_info.superstate_value == State.A
    assert state_a2_info.superstate_value == State.A
    assert state_a_info.superstate_value is None

    assert len(state_a_info.activate_actions) == 1

    assert len(state_a1_info.fixed_transitions) == 1
    assert state_a1_info.fixed_transitions[0].destination_state == SubA.A2


def test_get_info_ignore_internal_dynamic() -> None:
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).ignore_if(
        Trigger.IG, guard_always_true, "IgnoreGuard"
    ).internal_transition(
        Trigger.INT, action_sync, guard=guard_async, action_description="InternalAction"
    ).dynamic(Trigger.DYN, selector_sync, selector_description="DynamicSelector")

    info = sm.get_info()
    state_a_info = next(s for s in info.states if s.underlying_state == State.A)

    assert len(state_a_info.ignored_triggers) == 1
    ignored = state_a_info.ignored_triggers[0]
    assert ignored.trigger.underlying_trigger == Trigger.IG
    assert len(ignored.guard_conditions) == 1
    assert ignored.guard_conditions[0].method_description.description == "IgnoreGuard"

    assert len(state_a_info.internal_transitions) == 1
    internal = state_a_info.internal_transitions[0]
    assert internal.trigger.underlying_trigger == Trigger.INT
    assert len(internal.actions) == 1
    assert internal.actions[0].method_description.description == "InternalAction"
    assert len(internal.guard_conditions) == 1
    assert internal.guard_conditions[0].method_description.is_async is True

    assert len(state_a_info.dynamic_transitions) == 1
    dynamic = state_a_info.dynamic_transitions[0]
    assert dynamic.trigger.underlying_trigger == Trigger.DYN
    assert (
        dynamic.destination_state_selector_description.description == "DynamicSelector"
    )
    assert dynamic.guard_conditions == []


def test_get_info_trigger_parameters() -> None:
    sm = StateMachine[State, Trigger](State.A)
    sm.set_trigger_parameters(Trigger.X, int, str)
    sm.configure(State.A).permit(Trigger.X, State.B)

    info = sm.get_info()
    state_a_info = next(s for s in info.states if s.underlying_state == State.A)
    trans_x = state_a_info.fixed_transitions[0]

    assert trans_x.trigger.parameter_types == [int, str]
