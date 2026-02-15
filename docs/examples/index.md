# Examples

Project examples live in `examples/`.

## Included Scenarios

- `01_simple_phone_call.py`: basic transitions and machine info/graph output
- `02_bug_tracker.py`: external state storage and parameterized triggers
- `03_async_actions.py`: async entry/exit patterns
- `04_ignore_reentry.py`: ignore + reentry behavior
- `05_on_off.py`: minimal toggle machine
- `06_alarm_asyncio.py`: larger async orchestration workflow
- `07_json_serialization.py`: serializing domain state while machine logic remains configured in code
- `08_advanced_features.py`: mixed advanced features in one workflow

## Running an Example

```bash
uv run python examples/01_simple_phone_call.py
```

## Notes

Examples are practical demos, not exhaustive API specifications. For guaranteed behavior and signatures, use the API reference and test suite.
