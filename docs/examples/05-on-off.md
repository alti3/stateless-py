# 05: On Off Toggle

Source: `examples/05_on_off.py`

This is the smallest interactive example: a two-state toggle using string states and string triggers.

## Run

```bash
uv run python examples/05_on_off.py
```

## What This Example Covers

- Minimal machine setup
- String-based states/triggers (not just enums)
- Basic `permit(...)` transitions
- Repeated `fire(...)` in a loop

## Key APIs Used

```python
on_off_switch = StateMachine[str, str](OFF)
on_off_switch.configure(OFF).permit(TOGGLE, ON)
on_off_switch.configure(ON).permit(TOGGLE, OFF)
```

## Notes

- This example is intentionally simple and mirrors a "hello world" state machine.
- Pressing anything other than a space exits the loop.
