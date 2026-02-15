# Hierarchical States

`stateless-py` supports superstate/substate modeling.

## Declaring Hierarchy

```python
sm.configure(State.ChildA).substate_of(State.Parent)
sm.configure(State.ChildB).substate_of(State.Parent)
```

## Superstate Trigger Handling

If a substate does not handle a trigger, the machine searches superstates.

## Membership Queries

```python
sm.is_in_state(State.Parent)
```

Returns `True` when current state is the same as the queried state or nested under it.

## Initial Substate

```python
sm.configure(State.Parent).initial_transition(State.ChildA)
```

When entering `State.Parent`, the machine automatically enters `State.ChildA`.

## Action Ordering

For cross-hierarchy transitions, ordering is deterministic:

- Exit phase: deactivate/exit from deepest source toward common ancestor
- Entry phase: enter/activate from common ancestor toward deepest destination

For reentry (`source == destination`), the state runs its own deactivate/exit then entry/activate sequence.
