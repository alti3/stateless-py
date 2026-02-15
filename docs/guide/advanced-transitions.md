# Advanced Transitions

## Ignore

Use `ignore(...)` for accepted no-op triggers.

```python
sm.configure(State.A).ignore(Trigger.HEARTBEAT)
```

Guarded ignore:

```python
sm.configure(State.A).ignore_if(Trigger.HEARTBEAT, guard, "ignore when healthy")
```

## Reentry

Use reentry when a trigger should refresh the same state and rerun state lifecycle.

```python
sm.configure(State.A).permit_reentry(Trigger.REFRESH)
```

## Internal Transition

Internal transitions run actions without changing state.

```python
sm.configure(State.A).internal_transition(Trigger.PING, internal_action)
```

## Dynamic Transition

Dynamic transitions compute destination at runtime:

```python
def pick_destination(args):
    return State.B if args and args[0] else State.C

sm.configure(State.A).dynamic(Trigger.ROUTE, pick_destination)
```

Guarded dynamic:

```python
sm.configure(State.A).dynamic(
    Trigger.ROUTE,
    pick_destination,
    guard=is_routable,
    guard_description="routing enabled",
)
```
