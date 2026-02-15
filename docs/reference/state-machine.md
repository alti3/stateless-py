# StateMachine

## Constructor

```python
StateMachine(
    initial_state,
    state_accessor=None,
    state_mutator=None,
    firing_mode=FiringMode.IMMEDIATE,
    on_transitioned_callback=None,
    on_transitioned_async_callback=None,
    on_transition_completed_callback=None,
    on_transition_completed_async_callback=None,
)
```

## Core Methods

```python
state
configure(state)
fire(trigger, *args)
fire_async(trigger, *args)
can_fire(trigger, *args)
can_fire_async(trigger, *args)
get_permitted_triggers(*args)
get_permitted_triggers_async(*args)
```

## Handling and Introspection

```python
on_unhandled_trigger(handler)
on_unhandled_trigger_async(handler)
is_in_state(state)
set_trigger_parameters(trigger, *param_types)
get_info()
```

## Graph Methods

```python
generate_dot_graph()
generate_mermaid_graph()
visualize(filename="state_machine.gv", format="png", view=True)
```

## Lifecycle

```python
close_async()
```

Call `close_async()` when using `FiringMode.QUEUED` to stop queue processing cleanly.

## Behavior Notes

- `fire(...)` rejects async transition paths and raises `TypeError`.
- Missing valid transitions raise `InvalidTransitionError` unless an unhandled-trigger handler is registered.
- In queued mode, `fire(...)` is disallowed; use `fire_async(...)`.
- Transition callbacks can be sync or async via constructor parameters.
