# C# Stateless Parity

`stateless-py` is inspired by C# Stateless and implements most core concepts with Pythonic API conventions.

## Implemented Concepts

- Fluent state configuration
- Fixed, guarded, ignored, reentry, internal, and dynamic transitions
- Hierarchical states with initial substate support
- Entry/exit/activate/deactivate actions
- Async guards/actions/selectors with `fire_async`
- Introspection and graph export
- Immediate and queued firing modes

## Python-Specific Differences

- Trigger payloads are passed directly via `fire(..., *args)`
- Trigger parameter metadata (`set_trigger_parameters`) is introspection-oriented
- Transition callbacks are configured at `StateMachine` construction
- Async behavior is managed with `asyncio`

## Practical Guidance

Use the API as idiomatic Python rather than expecting one-to-one method names from C#.
