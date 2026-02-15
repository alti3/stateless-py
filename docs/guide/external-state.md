# External State Storage

`StateMachine` can read/write state through user-provided accessor and mutator functions.

## Why Use It

- State owned by a domain object
- Persistence-backed state
- Integrating with existing aggregate/root models

## Example

```python
external = {"state": State.A}

def get_state():
    return external["state"]

def set_state(new_state):
    external["state"] = new_state

sm = StateMachine[State, Trigger](
    State.A,
    state_accessor=get_state,
    state_mutator=set_state,
)
```

## Notes

- Accessor is used as source of truth for reads.
- Mutator is called during successful state transitions.
- Exceptions raised by accessor/mutator propagate to the caller.
- If accessor initial value differs from constructor `initial_state`, accessor value takes precedence after initialization.
