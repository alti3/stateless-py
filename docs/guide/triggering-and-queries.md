# Triggering and Queries

## Fire Triggers

- Sync: `sm.fire(trigger, *args)`
- Async: `await sm.fire_async(trigger, *args)`

## Check Trigger Availability

- Sync: `sm.can_fire(trigger, *args)`
- Async: `await sm.can_fire_async(trigger, *args)`

## List Permitted Triggers

- Sync: `sm.get_permitted_triggers(*args)`
- Async: `await sm.get_permitted_triggers_async(*args)`

In sync mode, triggers requiring async guard evaluation are not considered fireable.

## Unhandled Trigger Hooks

Register custom handling when no transition is valid.

```python
def on_unhandled(state, trigger, args):
    ...

sm.on_unhandled_trigger(on_unhandled)
```

Async variant:

```python
async def on_unhandled_async(state, trigger, args):
    ...

sm.on_unhandled_trigger_async(on_unhandled_async)
```

Without a handler, unhandled triggers raise `InvalidTransitionError`.

## Trigger Parameter Metadata

```python
sm.set_trigger_parameters(Trigger.ASSIGN, int, str)
```

This stores type metadata used by introspection models. It does not enforce runtime argument validation.
