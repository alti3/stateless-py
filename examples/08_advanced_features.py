from enum import Enum, auto
from typing import List

from stateless import StateMachine, Transition

# --- States ---
class PlayerState(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


class MediaState(Enum):
    AUDIO = auto()
    VIDEO = auto()


class Trigger(Enum):
    PLAY = auto()
    STOP = auto()
    PAUSE = auto()
    TOGGLE_MEDIA = auto()
    SET_VOLUME = auto()


# --- Log ---
log: List[str] = []


# --- Guard Condition ---
is_media_loaded = False


def check_media_loaded() -> bool:
    log.append(f"Guard Check: Media loaded? {is_media_loaded}")
    return is_media_loaded


# --- Actions ---
def log_action(message: str):
    def action(transition_or_none: Transition | None = None, args: tuple = ()):
        details = f" (Args: {args})" if args else ""
        if transition_or_none:
            log.append(
                f"{message} - Transition: {transition_or_none.source} -> {transition_or_none.destination} via {transition_or_none.trigger}{details}"
            )
        else:
            # For internal transitions, transition is None
            log.append(f"{message}{details}")

    return action


def activate_playing_scope():
    log.append("Activated: Playing Scope (e.g., acquire audio focus)")


def deactivate_playing_scope():
    log.append("Deactivated: Playing Scope (e.g., release audio focus)")


# --- State Machine Setup ---
# Use Enum as the common type for states
player = StateMachine[Enum, Trigger](PlayerState.STOPPED)

# --- Configuration ---

# STOPPED State
player.configure(PlayerState.STOPPED).permit_if(
    Trigger.PLAY, PlayerState.PLAYING, check_media_loaded, "Media must be loaded"
)

# PLAYING Superstate (contains AUDIO and VIDEO)
player.configure(PlayerState.PLAYING).on_activate(activate_playing_scope).on_deactivate(
    deactivate_playing_scope
).permit(Trigger.STOP, PlayerState.STOPPED).permit(
    Trigger.PAUSE, PlayerState.PAUSED
).internal_transition(
    Trigger.SET_VOLUME, log_action("Internal Action: Set Volume")
).initial_transition(
    MediaState.AUDIO
)  # Default to AUDIO when entering PLAYING

# AUDIO Substate
player.configure(MediaState.AUDIO).substate_of(PlayerState.PLAYING).on_entry(
    log_action("Entered Substate: AUDIO")
).permit(Trigger.TOGGLE_MEDIA, MediaState.VIDEO)

# VIDEO Substate
player.configure(MediaState.VIDEO).substate_of(PlayerState.PLAYING).on_entry(
    log_action("Entered Substate: VIDEO")
).permit(Trigger.TOGGLE_MEDIA, MediaState.AUDIO)

# PAUSED State
player.configure(PlayerState.PAUSED).permit(
    Trigger.PLAY, PlayerState.PLAYING
).permit(Trigger.STOP, PlayerState.STOPPED)


# --- Usage ---
def print_log_and_state(message: str):
    print(f"\n--- {message} ---")
    print(f"Current State: {player.state}")
    print("Log:")
    for entry in log:
        print(f"  - {entry}")
    log.clear()


print(f"Initial State: {player.state}")

# Try playing without media (Guard fails)
try:
    player.fire(Trigger.PLAY)
except Exception as e:
    print(f"\nError: {e}")
print_log_and_state("After trying PLAY (media not loaded)")

# "Load" media and try again (Guard passes)
is_media_loaded = True
player.fire(Trigger.PLAY)
# Enters PLAYING, activates scope, enters initial substate AUDIO
print_log_and_state("After PLAY (media loaded)")

# Use internal transition (doesn't change state or trigger activate/deactivate/entry/exit)
player.fire(Trigger.SET_VOLUME, 75)  # Pass volume argument
print_log_and_state("After SET_VOLUME")

# Toggle media type (within PLAYING superstate)
player.fire(Trigger.TOGGLE_MEDIA)
print_log_and_state("After TOGGLE_MEDIA (to VIDEO)")

# Pause the player (exits PLAYING scope)
player.fire(Trigger.PAUSE)
print_log_and_state("After PAUSE")

# Resume playing (re-enters PLAYING scope, should go to initial substate AUDIO)
player.fire(Trigger.PLAY)
print_log_and_state("After PLAY (resume)")

# Stop the player (exits PLAYING scope)
player.fire(Trigger.STOP)
print_log_and_state("After STOP")

# Try setting volume when stopped (invalid transition)
try:
    player.fire(Trigger.SET_VOLUME, 50)
except Exception as e:
    print(f"\nError: {e}")
print_log_and_state("After trying SET_VOLUME when STOPPED") 