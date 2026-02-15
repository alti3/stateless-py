# Actions

Actions execute at lifecycle points.

## Lifecycle Action Types

- `on_entry(action)`
- `on_entry_from(trigger, action)`
- `on_exit(action)`
- `on_activate(action)`
- `on_deactivate(action)`

## Sync and Async Actions

Both sync and async actions are supported.

- Sync action example:

```python
def on_entry(transition):
    print("entered", transition.destination)
```

- Async action example:

```python
async def on_entry_async(transition):
    ...

await sm.fire_async(Trigger.X)
```

If async actions are involved, calling `fire(...)` raises `TypeError`.

## Action Signatures

Action wrappers support callables that consume transition context and/or trigger args.

Recommended signatures:

- Entry/internal action with transition context and all fired args tuple:

```python
def action(transition, args):
    ...
```

- Exit action:

```python
def on_exit(transition):
    ...
```

- Activate/deactivate action:

```python
def on_activate():
    ...
```

For robustness, keep action signatures explicit and simple.

## `on_entry_from`

`on_entry_from(trigger, action)` runs only when entry was caused by that trigger.

Useful for parameterized workflows where one state has multiple incoming transitions.
