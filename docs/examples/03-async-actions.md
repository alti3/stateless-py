# 03: Async Actions

Source: `examples/03_async_actions.py`

This example demonstrates async entry and exit actions and verifies execution order using `fire_async(...)`.

## Run

```bash
uv run python examples/03_async_actions.py
```

## What This Example Covers

- Async handlers with `on_entry_async(...)` and `on_exit_async(...)`
- Async trigger firing with `await sm.fire_async(...)`
- Transition ordering across async actions
- Assertion-based verification of expected behavior

## Key APIs Used

```python
async_machine.configure(State.EXECUTING).on_entry_async(
    on_entry_executing
).on_exit_async(on_exit_executing).permit(Trigger.FINISH, State.FINISHED)

await async_machine.fire_async(Trigger.START)
await async_machine.fire_async(Trigger.FINISH)
```

## Notes

- The script is runnable directly and is also decorated for `pytest-asyncio`.
- Use this pattern when any guard, action, or callback is asynchronous.
