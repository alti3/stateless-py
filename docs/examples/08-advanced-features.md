# 08: Advanced Features

Source: `examples/08_advanced_features.py`

This example combines several advanced APIs in one media-player style workflow.

## Run

```bash
uv run python examples/08_advanced_features.py
```

## What This Example Covers

- Guarded transitions with `permit_if(...)`
- Superstate/substate hierarchy with `substate_of(...)`
- Superstate activation hooks with `on_activate(...)` and `on_deactivate(...)`
- Internal transitions with `internal_transition(...)`
- Initial substate selection with `initial_transition(...)`
- Mixed enum types via `StateMachine[Enum, Trigger]`

## Key APIs Used

```python
player.configure(PlayerState.STOPPED).permit_if(
    Trigger.PLAY, PlayerState.PLAYING, check_media_loaded, "Media must be loaded"
)

player.configure(PlayerState.PLAYING).internal_transition(
    Trigger.SET_VOLUME, log_action("Internal Action: Set Volume")
).initial_transition(MediaState.AUDIO)
```

## Notes

- The example is useful as a compact "feature matrix" for common advanced patterns.
- It also demonstrates how internal transitions avoid state exit/entry cycles.
