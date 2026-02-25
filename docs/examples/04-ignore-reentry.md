# 04: Ignore and Reentry

Source: `examples/04_ignore_reentry.py`

This example contrasts ignored triggers with reentry transitions, and shows their effect on entry/exit actions.

## Run

```bash
uv run python examples/04_ignore_reentry.py
```

## What This Example Covers

- Ignoring triggers in a state with `ignore(...)`
- Re-firing in the same state with `permit_reentry(...)`
- Logging entry and exit behavior to validate semantics
- Error behavior when a trigger is not configured

## Key APIs Used

```python
sm.configure(State.A).on_entry(on_entry("A")).on_exit(on_exit("A")).permit(
    Trigger.STEP, State.B
).ignore(Trigger.IGNORE_ME).permit_reentry(Trigger.REENTER)
```

## Notes

- `ignore(...)` keeps state unchanged and runs no transition actions.
- `permit_reentry(...)` exits and re-enters the same state, so exit/entry handlers run.
