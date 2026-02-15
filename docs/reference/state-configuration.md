# StateConfiguration

`StateConfiguration` is returned by `StateMachine.configure(state)`.

## Transition Methods

```python
permit(trigger, destination_state, guard=(), guard_description=None, *, guards=None)
permit_if(trigger, destination_state, guard, guard_description=None)
permit_reentry(trigger, guard=(), guard_description=None, *, guards=None)
permit_reentry_if(trigger, guard, guard_description=None)
ignore(trigger, guard=(), guard_description=None, *, guards=None)
ignore_if(trigger, guard, guard_description=None)
internal_transition(
    trigger,
    action,
    guard=(),
    guard_description=None,
    action_description=None,
    *,
    guards=None,
)
dynamic(
    trigger,
    destination_selector,
    guard=(),
    guard_description=None,
    selector_description=None,
    *,
    guards=None,
)
```

## Action Methods

```python
on_entry(entry_action, description=None)
on_entry_from(trigger, entry_action, description=None)
on_exit(exit_action, description=None)
on_activate(activate_action, description=None)
on_deactivate(deactivate_action, description=None)
```

## Hierarchy Methods

```python
substate_of(superstate)
initial_transition(target_state)
```

## Notes

- Methods are chainable and return the same `StateConfiguration` instance.
- Trigger values must be hashable.
- Guard lists are modeled as `(callable, description)` tuples.
- `initial_transition(target_state)` requires `target_state` to be within the configured superstate subtree.
