# Core Concepts

## State Machine

`StateMachine[StateT, TriggerT]` is the runtime engine. It holds state configuration, evaluates guards, executes actions, and updates state.

## States and Triggers

- `StateT`: any hashable Python object (Enums are recommended)
- `TriggerT`: any hashable Python object

## Transition

A `Transition` model captures a fired transition:

- `source`
- `destination`
- `trigger`
- `parameters` (tuple of args passed to `fire` / `fire_async`)
- `is_reentry`

## Configuration Flow

1. Create machine with initial state.
2. Call `configure(state)`.
3. Chain configuration methods (`permit`, `on_entry`, `ignore`, etc.).
4. Fire triggers.

## Sync vs Async

- `fire(...)` executes synchronously and rejects async guards/actions/selectors.
- `fire_async(...)` supports both sync and async handlers.

## Immediate vs Queued Processing

- `FiringMode.IMMEDIATE` (default): trigger is processed immediately.
- `FiringMode.QUEUED`: trigger is enqueued and processed sequentially by an internal async queue processor.
