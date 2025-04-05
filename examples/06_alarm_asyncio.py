import asyncio
import logging
from enum import Enum, auto
from typing import Any

from stateless import StateMachine, Transition

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# --- States ---
class AlarmState(Enum):
    UNDEFINED = auto()
    DISARMED = auto()
    PREARMED = auto()  # Temporary state with arm delay
    ARMED = auto()
    PRETRIGGERED = auto()  # Temporary state with trigger delay
    TRIGGERED = auto()  # Temporary state with timeout
    ARMPAUSED = auto()  # Temporary state with pause delay
    ACKNOWLEDGED = auto()


# --- Triggers ---
class AlarmCommand(Enum):
    STARTUP = auto()
    ARM = auto()
    DISARM = auto()
    TRIGGER = auto()
    ACKNOWLEDGE = auto()
    PAUSE = auto()
    TIMEOUT = auto()  # Internal trigger fired by timers


# --- Alarm Class ---
class Alarm:
    def __init__(
        self,
        arm_delay_sec: int,
        pause_delay_sec: int,
        trigger_delay_sec: int,
        trigger_timeout_sec: int,
    ):
        self._state = AlarmState.UNDEFINED
        self._machine = StateMachine[AlarmState, AlarmCommand](
            lambda: self._state, lambda s: self._set_state(s)
        )
        self._timers: dict[str, asyncio.Task[Any] | None] = {
            "pre_arm": None,
            "pause": None,
            "trigger_delay": None,
            "trigger_timeout": None,
        }
        self._delays = {
            "pre_arm": arm_delay_sec,
            "pause": pause_delay_sec,
            "trigger_delay": trigger_delay_sec,
            "trigger_timeout": trigger_timeout_sec,
        }

        self._configure_machine()
        # Automatically fire startup after configuration
        asyncio.create_task(self._machine.fire_async(AlarmCommand.STARTUP))

    def _set_state(self, new_state: AlarmState):
        logging.info(f"State changing from {self._state} to {new_state}")
        self._state = new_state

    @property
    def state(self) -> AlarmState:
        return self._machine.state

    async def fire(self, command: AlarmCommand):
        if self._machine.can_fire(command):  # Use sync can_fire for quick check
            logging.info(f"Firing command: {command}")
            # Use fire_async as timer actions are async
            await self._machine.fire_async(command)
        else:
            logging.warning(
                f"Cannot fire command '{command}' from state '{self.state}'"
            )
            # raise InvalidOperationException(f"Cannot transition from {self.state} via {command}")

    def _configure_machine(self):
        self._machine.on_transitioned(self._log_transition)

        self._machine.configure(AlarmState.UNDEFINED).permit(
            AlarmCommand.STARTUP, AlarmState.DISARMED
        )

        self._machine.configure(AlarmState.DISARMED).permit(
            AlarmCommand.ARM, AlarmState.PREARMED
        )

        self._machine.configure(AlarmState.ARMED).permit(
            AlarmCommand.DISARM, AlarmState.DISARMED
        ).permit(AlarmCommand.TRIGGER, AlarmState.PRETRIGGERED).permit(
            AlarmCommand.PAUSE, AlarmState.ARMPAUSED
        )

        self._machine.configure(AlarmState.PREARMED).on_entry_async(
            lambda t: self._start_timer("pre_arm")
        ).on_exit_async(lambda t: self._cancel_timer("pre_arm")).permit(
            AlarmCommand.TIMEOUT, AlarmState.ARMED
        ).permit(AlarmCommand.DISARM, AlarmState.DISARMED)

        self._machine.configure(AlarmState.ARMPAUSED).on_entry_async(
            lambda t: self._start_timer("pause")
        ).on_exit_async(lambda t: self._cancel_timer("pause")).permit(
            AlarmCommand.TIMEOUT, AlarmState.ARMED
        ).permit(
            AlarmCommand.TRIGGER, AlarmState.PRETRIGGERED
        )  # Can be triggered while paused

        self._machine.configure(AlarmState.PRETRIGGERED).on_entry_async(
            lambda t: self._start_timer("trigger_delay")
        ).on_exit_async(lambda t: self._cancel_timer("trigger_delay")).permit(
            AlarmCommand.TIMEOUT, AlarmState.TRIGGERED
        ).permit(AlarmCommand.DISARM, AlarmState.DISARMED)

        self._machine.configure(AlarmState.TRIGGERED).on_entry_async(
            lambda t: self._start_timer("trigger_timeout")
        ).on_exit_async(lambda t: self._cancel_timer("trigger_timeout")).permit(
            AlarmCommand.TIMEOUT, AlarmState.ARMED
        ).permit(AlarmCommand.ACKNOWLEDGE, AlarmState.ACKNOWLEDGED)

        self._machine.configure(AlarmState.ACKNOWLEDGED).permit(
            AlarmCommand.DISARM, AlarmState.DISARMED
        )

    async def _timer_task(self, delay_sec: int, timer_name: str):
        try:
            await asyncio.sleep(delay_sec)
            logging.info(f"Timer '{timer_name}' finished, firing TIMEOUT.")
            # Fire TIMEOUT command - needs to be async as it might trigger async actions
            await self._machine.fire_async(AlarmCommand.TIMEOUT)
        except asyncio.CancelledError:
            logging.info(f"Timer '{timer_name}' cancelled.")
        except Exception as e:
            logging.error(f"Error in timer '{timer_name}': {e}")

    async def _start_timer(self, timer_name: str):
        await self._cancel_timer(timer_name)  # Ensure previous one is cancelled
        delay = self._delays.get(timer_name)
        if delay is not None and delay > 0:
            logging.info(f"Starting timer '{timer_name}' for {delay} seconds.")
            self._timers[timer_name] = asyncio.create_task(
                self._timer_task(delay, timer_name)
            )
        else:
            logging.warning(
                f"Timer '{timer_name}' has invalid delay {delay}, not starting."
            )

    async def _cancel_timer(self, timer_name: str):
        task = self._timers.get(timer_name)
        if task and not task.done():
            logging.info(f"Cancelling timer '{timer_name}'.")
            task.cancel()
            try:
                await task  # Allow cancellation to propagate
            except asyncio.CancelledError:
                pass  # Expected
        self._timers[timer_name] = None

    def _log_transition(self, transition: Transition):
        logging.info(
            f"Transitioned: {transition.source} -> {transition.destination} via {transition.trigger}"
        )

    async def cleanup(self):
        """Cancel any running timers."""
        logging.info("Cleaning up alarm timers...")
        for name in list(self._timers.keys()):
            await self._cancel_timer(name)
        logging.info("Cleanup complete.")


# --- Usage Example ---
async def run_alarm_scenario():
    print("\n--- Alarm Scenario ---")
    alarm = Alarm(
        arm_delay_sec=3, pause_delay_sec=4, trigger_delay_sec=2, trigger_timeout_sec=5
    )

    # Wait for startup
    await asyncio.sleep(0.1)
    print(f"Initial State: {alarm.state}")

    # Arm sequence
    await alarm.fire(AlarmCommand.ARM)
    print(f"State after ARM: {alarm.state}")  # Should be PREARMED
    print(f"Waiting for arm delay ({alarm._delays['pre_arm']}s)...")
    await asyncio.sleep(alarm._delays["pre_arm"] + 0.5)  # Wait for timer
    print(f"State after arm delay: {alarm.state}")  # Should be ARMED

    # Trigger sequence
    await alarm.fire(AlarmCommand.TRIGGER)
    print(f"State after TRIGGER: {alarm.state}")  # Should be PRETRIGGERED
    print(f"Waiting for trigger delay ({alarm._delays['trigger_delay']}s)...")
    await asyncio.sleep(alarm._delays["trigger_delay"] + 0.5)
    print(f"State after trigger delay: {alarm.state}")  # Should be TRIGGERED

    # Acknowledge
    await alarm.fire(AlarmCommand.ACKNOWLEDGE)
    print(f"State after ACKNOWLEDGE: {alarm.state}")  # Should be ACKNOWLEDGED

    # Disarm
    await alarm.fire(AlarmCommand.DISARM)
    print(f"State after DISARM: {alarm.state}")  # Should be DISARMED

    # Test pause sequence
    await alarm.fire(AlarmCommand.ARM)
    await asyncio.sleep(alarm._delays["pre_arm"] + 0.5)  # Wait for arming
    print(f"\nState after re-arming: {alarm.state}")  # ARMED
    await alarm.fire(AlarmCommand.PAUSE)
    print(f"State after PAUSE: {alarm.state}")  # ARMPAUSED
    print(f"Waiting for pause delay ({alarm._delays['pause']}s)...")
    await asyncio.sleep(alarm._delays["pause"] + 0.5)
    print(f"State after pause delay: {alarm.state}")  # Should be ARMED again

    # Test trigger timeout
    await alarm.fire(AlarmCommand.TRIGGER)
    await asyncio.sleep(alarm._delays["trigger_delay"] + 0.5)  # Wait for trigger delay
    print(f"\nState after trigger delay (again): {alarm.state}")  # TRIGGERED
    print(f"Waiting for trigger timeout ({alarm._delays['trigger_timeout']}s)...")
    await asyncio.sleep(alarm._delays["trigger_timeout"] + 0.5)
    print(f"State after trigger timeout: {alarm.state}")  # Should be ARMED

    await alarm.cleanup()


if __name__ == "__main__":
    asyncio.run(run_alarm_scenario())
