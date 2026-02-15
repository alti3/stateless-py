# Guards

Guards control whether a configured behavior is valid for a fired trigger.

## Where Guards Apply

- `permit(...)`
- `permit_if(...)`
- `permit_reentry(...)`
- `permit_reentry_if(...)`
- `ignore(...)`
- `ignore_if(...)`
- `internal_transition(...)`
- `dynamic(...)`

## Guard Types

- Sync: `def guard(...) -> bool`
- Async: `async def guard(...) -> bool`

## Sync and Async Rules

- `fire(...)` only supports sync guards.
- `fire_async(...)` supports sync and async guards.
- `can_fire(...)` and `get_permitted_triggers(...)` skip/raise when async guards are involved.
- `can_fire_async(...)` and `get_permitted_triggers_async(...)` evaluate async guards.

## Guard Arguments

Guard functions can inspect trigger arguments. Guards receive a compatible prefix of the fired args.

```python
def guard(order_total: float) -> bool:
    return order_total >= 100.0

sm.configure(State.A).permit_if(Trigger.X, State.B, guard)
sm.fire(Trigger.X, 120.0)
```

## Guard Failure Behavior

When a trigger is valid but guard conditions fail, `InvalidTransitionError` is raised and includes unmet guard descriptions when provided.
