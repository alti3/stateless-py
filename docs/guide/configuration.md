# Configuration

`configure(state)` returns `StateConfiguration`, a fluent builder for one state.

## Fixed Transitions

```python
sm.configure(State.A).permit(Trigger.X, State.B)
```

Guarded form:

```python
sm.configure(State.A).permit(
    Trigger.X,
    State.B,
    guard=my_guard,
    guard_description="Must pass guard",
)
```

Or with multiple guards:

```python
sm.configure(State.A).permit(
    Trigger.X,
    State.B,
    guards=[(guard1, "g1"), (guard2, "g2")],
)
```

Convenience:

```python
sm.configure(State.A).permit_if(Trigger.X, State.B, my_guard, "g1")
```

## Reentry

```python
sm.configure(State.A).permit_reentry(Trigger.REENTER)
sm.configure(State.A).permit_reentry_if(Trigger.REENTER, guard, "guard")
```

Reentry performs exit + entry (and deactivate + activate) for the same state.

## Ignore

```python
sm.configure(State.A).ignore(Trigger.NOOP)
sm.configure(State.A).ignore_if(Trigger.NOOP, guard, "ignore guard")
```

## Internal Transition

```python
sm.configure(State.A).internal_transition(Trigger.PING, internal_action)
```

Internal transitions execute an action without changing state.

## Dynamic Transition

```python
sm.configure(State.A).dynamic(Trigger.ROUTE, selector)
```

`selector` computes destination state at runtime.

## Hierarchy

```python
sm.configure(State.Child).substate_of(State.Parent)
sm.configure(State.Parent).initial_transition(State.Child)
```

## Actions

```python
(
    sm.configure(State.A)
    .on_entry(on_entry)
    .on_entry_from(Trigger.X, on_entry_from_x)
    .on_exit(on_exit)
    .on_activate(on_activate)
    .on_deactivate(on_deactivate)
)
```
