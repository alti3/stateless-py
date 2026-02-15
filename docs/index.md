# Stateless-py

`stateless-py` is a Python state machine library inspired by the C# `Stateless` project. It provides a fluent API for configuring transitions, guards, actions, hierarchical states, and async workflows.

## What You Can Build

- Workflow engines and approval flows
- Domain aggregates with explicit lifecycle rules
- Async orchestration with queued trigger processing
- Systems that need runtime introspection and graph visualization

## Key Features

- Fluent configuration API via `configure(...)`
- Transition guards (`permit_if`, `ignore_if`, guarded `dynamic`, guarded `internal_transition`)
- Entry/exit/activate/deactivate actions (sync and async)
- Reentry transitions and internal transitions
- Hierarchical states (`substate_of`, `initial_transition`)
- Async trigger firing (`fire_async`) plus queued trigger mode (`FiringMode.QUEUED`)
- Introspection via Pydantic reflection models (`get_info()`)
- Diagram generation in DOT and Mermaid

## Minimal Example

```python
from enum import Enum, auto
from stateless import StateMachine

class State(Enum):
    OFF = auto()
    ON = auto()

class Trigger(Enum):
    TOGGLE = auto()

sm = StateMachine[State, Trigger](State.OFF)
sm.configure(State.OFF).permit(Trigger.TOGGLE, State.ON)
sm.configure(State.ON).permit(Trigger.TOGGLE, State.OFF)

sm.fire(Trigger.TOGGLE)
assert sm.state == State.ON
```

## Documentation Map

- Start with `Getting Started` for installation and first use.
- Use `Guide` for behavior and design patterns.
- Use `API Reference` for signatures and method-level behavior.
- Use `Introspection` and `Architecture` for system-level understanding.
