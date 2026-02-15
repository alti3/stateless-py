# Introspection Overview

`get_info()` returns a `StateMachineInfo` Pydantic model describing configured states and transitions.

## Top-Level Model

`StateMachineInfo` includes:

- `states: list[StateInfo]`
- `state_type: type`
- `trigger_type: type`
- `initial_state`

## `StateInfo`

Each state includes:

- underlying state value
- entry/exit/activate/deactivate action metadata
- substate relationships and superstate value
- fixed transitions
- internal transitions
- ignored triggers
- dynamic transitions
- initial transition target (if configured)

## Example

```python
info = sm.get_info()

for state in info.states:
    print(state.underlying_state)
    for t in state.fixed_transitions:
        print(" ", t.trigger.underlying_trigger, "->", t.destination_state)
```

## Trigger Metadata

If you configure trigger parameter metadata with `set_trigger_parameters(...)`, it appears in `TriggerInfo.parameter_types` inside introspection output.
