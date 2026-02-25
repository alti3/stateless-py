# 01: Simple Phone Call

Source: `examples/01_simple_phone_call.py`

This example builds a phone-call workflow and walks through multiple transitions, then prints reflection metadata and generates a graph image.

## Run

```bash
uv run python examples/01_simple_phone_call.py
```

## What This Example Covers

- Basic `StateMachine` configuration with `permit(...)`
- Transitioning through a realistic call flow
- Handling invalid transitions with exceptions
- Introspection with `get_info()`
- Graph rendering with `visualize(...)`

## Key APIs Used

```python
phone_call.configure(State.OFF_HOOK).permit(Trigger.CALL_DIALED, State.RINGING)

phone_call.fire(Trigger.CALL_DIALED)
info = phone_call.get_info()
phone_call.visualize("phone_call.png", view=False)
```

## Notes

- Graph export requires the Python `graphviz` package and the `dot` executable on your `PATH`.
- The example configures a "destroyed phone" state to demonstrate a terminal-like workflow.
