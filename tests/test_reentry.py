import pytest
from enum import Enum, auto

from stateless import StateMachine, InvalidTransitionError

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()


class Trigger(Enum):
    REENTER = auto()
    MOVE = auto()


actions_log: list[str] = []


def setup_function():
    actions_log.clear()


def entry(s):
    return lambda t: actions_log.append(f"entry_{s.name}")


def exit_(s):
    return lambda t: actions_log.append(f"exit_{s.name}")


def activate(s):
    return lambda t: actions_log.append(f"activate_{s.name}")


def deactivate(s):
    return lambda t: actions_log.append(f"deactivate_{s.name}")


# --- Basic Reentry ---


@pytest.mark.asyncio
async def test_permit_reentry_executes_exit_entry():
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_entry(entry(State.A)).on_exit(
        exit_(State.A)
    ).permit_reentry(Trigger.REENTER).permit(Trigger.MOVE, State.B)

    await sm.fire_async(Trigger.REENTER)
    assert sm.state == State.A
    # Reentry should trigger exit then entry of the same state
    assert actions_log == ["exit_State.A", "entry_State.A"]


@pytest.mark.asyncio
async def test_permit_reentry_executes_deactivate_activate():
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_activate(activate(State.A)).on_deactivate(
        deactivate(State.A)
    ).permit_reentry(Trigger.REENTER)

    await sm.fire_async(Trigger.REENTER)
    assert sm.state == State.A
    # Reentry should trigger deactivate then activate
    assert actions_log == ["deactivate_State.A", "activate_State.A"]


# --- Reentry with Guards ---


@pytest.mark.asyncio
async def test_permit_reentry_if_guard_met():
    can_reenter = True

    def guard():
        return can_reenter

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_exit(exit_(State.A)).on_entry(
        entry(State.A)
    ).permit_reentry_if(Trigger.REENTER, guard)

    await sm.fire_async(Trigger.REENTER)
    assert sm.state == State.A
    assert actions_log == ["exit_State.A", "entry_State.A"]


@pytest.mark.asyncio
async def test_permit_reentry_if_guard_not_met():
    can_reenter = False

    def guard():
        return can_reenter

    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_exit(exit_(State.A)).on_entry(
        entry(State.A)
    ).permit_reentry_if(Trigger.REENTER, guard, "ReentryGuard")

    with pytest.raises(InvalidTransitionError) as excinfo:
        await sm.fire_async(Trigger.REENTER)
    assert sm.state == State.A
    assert actions_log == []
    assert "ReentryGuard" in str(excinfo.value)


# --- Reentry vs Standard Transition ---


@pytest.mark.asyncio
async def test_reentry_does_not_affect_other_transitions():
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).on_exit(exit_(State.A)).on_entry(
        entry(State.A)
    ).permit_reentry(Trigger.REENTER).permit(
        Trigger.MOVE, State.B
    )  # Standard transition
    sm.configure(State.B).on_entry(entry(State.B))

    await sm.fire_async(Trigger.MOVE)  # A -> B
    assert sm.state == State.B
    assert actions_log == ["exit_State.A", "entry_State.B"]
