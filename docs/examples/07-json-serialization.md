# 07: JSON Serialization

Source: `examples/07_json_serialization.py`

This example shows how to serialize domain state to JSON while rebuilding state-machine configuration in code during deserialization.

## Run

```bash
uv run python examples/07_json_serialization.py
```

## What This Example Covers

- Persisting state as data (`to_dict`, `to_json`)
- Restoring domain objects from JSON (`from_dict`, `from_json`)
- Recreating the machine with the restored state
- Equality checks between original and deserialized objects

## Key APIs Used

```python
sm = StateMachine(
    current_state,
    state_accessor=lambda: self._state,
    state_mutator=self._set_state,
)

return {
    "name": self.name,
    "state": self.state.name,
}
```

## Notes

- The example persists domain data, not the full machine configuration graph.
- This keeps workflow rules explicit in source code while still supporting durable state.
