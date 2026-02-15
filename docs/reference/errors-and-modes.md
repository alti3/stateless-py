# Errors and Firing Modes

## Exceptions

- `StatelessError`: base exception type
- `InvalidTransitionError`: invalid trigger path or guard failure
- `ConfigurationError`: invalid configuration setup

## Typical Error Scenarios

- firing an unconfigured trigger without unhandled trigger handler
- guard conditions not met
- calling `fire(...)` when async behavior is required
- invalid hierarchy setup (for example invalid initial transition target)

## FiringMode

```python
from stateless import FiringMode

FiringMode.IMMEDIATE
FiringMode.QUEUED
```

- `IMMEDIATE`: process trigger immediately
- `QUEUED`: queue triggers and process sequentially in async context
