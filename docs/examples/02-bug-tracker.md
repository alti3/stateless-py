# 02: Bug Tracker

Source: `examples/02_bug_tracker.py`

This example models an issue lifecycle (`OPEN -> ASSIGNED -> DEFERRED/CLOSED`) using external state storage on a domain object.

## Run

```bash
uv run python examples/02_bug_tracker.py
```

## What This Example Covers

- External state storage via `state_accessor` and `state_mutator`
- Trigger payloads with `set_trigger_parameters(...)`
- Entry actions bound to specific triggers with `on_entry_from(...)`
- Reentry transitions with `permit_reentry(...)`
- Hierarchy with `substate_of(...)`
- Capability checks and invalid-transition handling

## Key APIs Used

```python
sm = StateMachine(
    initial_state,
    state_accessor=lambda: self._state,
    state_mutator=lambda s: self._set_state(s),
)

sm.configure(State.ASSIGNED).on_entry_from(Trigger.ASSIGN, self._assign)
sm.set_trigger_parameters(Trigger.ASSIGN, str)
```

## Notes

- The `Bug` class owns workflow behavior, while the machine drives allowed transitions.
- The example also prints reflection data and generates a graph image.
