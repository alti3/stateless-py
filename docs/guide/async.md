# Async and Firing Modes

## Async Firing

Use `await sm.fire_async(trigger, *args)` when any of these are async:

- guard
- action
- dynamic destination selector
- unhandled-trigger handler
- transition callbacks

## Sync Firing

`sm.fire(...)` is for fully synchronous transition paths.

`fire(...)` raises `TypeError` when it encounters async behavior.

## Firing Modes

### `FiringMode.IMMEDIATE`

Default mode. Trigger is processed immediately in the current call.

### `FiringMode.QUEUED`

Triggers are placed on an internal `asyncio.Queue` and processed sequentially.

```python
from stateless import FiringMode, StateMachine
sm = StateMachine(State.A, firing_mode=FiringMode.QUEUED)
await sm.fire_async(Trigger.X)
```

In queued mode:

- `fire(...)` is not allowed.
- Processing is serialized.
- Failures for queued items are handled inside queue processing and do not crash the processor.
- You should call `await sm.close_async()` during shutdown to stop the processor cleanly.

## Transition Callbacks

`StateMachine(...)` constructor accepts callbacks:

- `on_transitioned_callback`
- `on_transitioned_async_callback`
- `on_transition_completed_callback`
- `on_transition_completed_async_callback`

`on_transitioned*` is invoked before transition actions are executed.

`on_transition_completed*` is invoked after transition actions are complete.
