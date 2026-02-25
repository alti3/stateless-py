# 06: Alarm Asyncio Workflow

Source: `examples/06_alarm_asyncio.py`

This example builds a larger async alarm workflow with timed transitions, pause/trigger windows, and cleanup of running tasks.

## Run

```bash
uv run python examples/06_alarm_asyncio.py
```

## What This Example Covers

- Async state machine orchestration for real workflows
- Timer-driven transitions using `asyncio.create_task(...)`
- Automatic trigger firing from async timer completion
- Async entry/exit actions for starting and canceling timers
- Transition callbacks with `on_transitioned(...)`

## Key APIs Used

```python
self._machine.configure(AlarmState.PREARMED).on_entry_async(
    lambda t: self._start_timer("pre_arm")
).on_exit_async(lambda t: self._cancel_timer("pre_arm")).permit(
    AlarmCommand.TIMEOUT, AlarmState.ARMED
)

await self._machine.fire_async(AlarmCommand.TIMEOUT)
```

## Notes

- The workflow demonstrates how to embed a `StateMachine` into a domain service class.
- `cleanup()` is important to cancel pending timer tasks when shutting down.
