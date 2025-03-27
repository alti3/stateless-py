"""
The main StateMachine class.
"""

# Placeholder - Core implementation to follow
from typing import (
    Generic,
    Optional,
    Callable,
    Sequence,
    Any,
    Dict,
    Type,
    List,
    Awaitable,
    Union,
    Tuple,
    cast,
)
from enum import Enum
import asyncio
import threading  # For potential future locking
import inspect  # Added

from .state_representation import StateRepresentation, Args  # Assuming this will exist
from .state_configuration import StateConfiguration  # Assuming this will exist
from .transition import (
    StateT,
    TriggerT,
    Transition,
    UnmetTriggerHandler,
    UnmetTriggerHandlerAsync,
)
from .exceptions import InvalidTransitionError, ConfigurationError, StatelessError
from .firing_modes import FiringMode
from .reflection import (
    StateMachineInfo,
    StateInfo,
    ActionInfo,
    TransitionInfo,
    IgnoredTransitionInfo,
    DynamicTransitionInfo,
    GuardInfo,
    TriggerInfo,
    InternalTransitionInfo,
)  # Added InternalTransitionInfo
from .trigger_behaviour import (
    TriggerBehaviour,
    IgnoredTriggerBehaviour,
    ReentryTriggerBehaviour,
    InternalTriggerBehaviour,
    TransitioningTriggerBehaviour,
    DynamicTriggerBehaviour,
)


# Placeholder implementation
class StateMachine(Generic[StateT, TriggerT]):
    """
    A configurable state machine.
    """

    def __init__(
        self,
        initial_state: StateT,
        state_accessor: Optional[Callable[[], StateT]] = None,
        state_mutator: Optional[Callable[[StateT], None]] = None,
        firing_mode: FiringMode = FiringMode.IMMEDIATE,
    ):
        self._initial_state = initial_state
        self._state_accessor = state_accessor
        self._state_mutator = state_mutator
        self._firing_mode = firing_mode  # TODO: Implement queuing if QUEUED
        self._state_representations: Dict[
            StateT, StateRepresentation[StateT, TriggerT]
        ] = {}
        self._unmet_trigger_handler: UnmetTriggerHandler[StateT, TriggerT] = None
        self._unmet_trigger_handler_async: UnmetTriggerHandlerAsync[
            StateT, TriggerT
        ] = None
        self._state_type: Optional[Type] = None
        self._trigger_type: Optional[Type] = None
        self._lock = (
            threading.Lock()
        )  # Basic lock for thread safety on state changes/config access
        self._firing = False  # Simple flag to detect reentrant firing (sync only)
        self._queue = (
            asyncio.Queue[Tuple[TriggerT, Sequence[Any]]]()
            if firing_mode == FiringMode.QUEUED
            else None
        )
        self._queue_processor_task: Optional[asyncio.Task] = None
        self._queue_started = False  # Flag to track if processor started
        self._trigger_param_types: Dict[
            TriggerT, List[Type]
        ] = {}  # Store explicit param types

        # Determine state/trigger types (best effort)
        if isinstance(initial_state, Enum):
            self._state_type = type(initial_state)
        else:
            self._state_type = type(initial_state)  # Or keep as None?

        # Initialize current state
        if self._state_accessor and self._state_mutator:
            # External state management - ensure initial state matches if possible
            # Or should we set the external state to initial_state here? C# seems to read first.
            self._current_state = self._state_accessor()
            # TODO: What if external state != initial_state? Raise error? Set external?
        else:
            self._current_state = initial_state
            self._state_accessor = lambda: self._current_state
            self._state_mutator = self._set_internal_state

        # TODO: Add lock for thread safety if needed, especially for QUEUED mode

        # Defer starting queue processor until first async fire if no loop running
        if self._firing_mode == FiringMode.QUEUED:
            self._ensure_queue_processor_started()  # Try starting now if possible

    def _set_internal_state(self, new_state: StateT) -> None:
        self._current_state = new_state

    @property
    def state(self) -> StateT:
        """The current state of the machine."""
        if self._state_accessor:
            return self._state_accessor()
        raise RuntimeError(
            "State accessor not configured."
        )  # Should not happen with default

    def configure(self, state: StateT) -> "StateConfiguration[StateT, TriggerT]":
        """Begin configuration of the specified state."""
        # TODO: Implement StateConfiguration and StateRepresentation lookup/creation
        representation = self._get_or_add_state_representation(state)
        return StateConfiguration(
            self, representation, self._get_or_add_state_representation
        )

    def _get_or_add_state_representation(
        self, state: StateT
    ) -> "StateRepresentation[StateT, TriggerT]":
        """Looks up or creates a StateRepresentation for the given state."""
        # TODO: Implement actual logic
        if state not in self._state_representations:
            # Placeholder: Create a new representation
            self._state_representations[state] = StateRepresentation(state)  # type: ignore[call-arg] # Placeholder
        return self._state_representations[state]

    def _ensure_queue_processor_started(self) -> None:
        """Starts the queue processor task if not already started and if possible."""
        if self._firing_mode == FiringMode.QUEUED and not self._queue_started:
            try:
                loop = asyncio.get_running_loop()
                if (
                    self._queue_processor_task is None
                    or self._queue_processor_task.done()
                ):
                    self._queue_processor_task = loop.create_task(self._process_queue())
                    self._queue_started = True
            except RuntimeError:
                # No loop running, will try again on next fire_async
                self._queue_started = False
            except Exception as e:
                # Log or handle other potential errors during task creation
                print(f"Error starting queue processor: {e}")
                self._queue_started = False

    async def _process_queue(self) -> None:
        """Processes triggers from the queue sequentially."""
        if not self._queue:
            return
        print("Queue processor started.")  # Debugging
        while True:
            try:
                trigger, args = await self._queue.get()
                print(
                    f"Processing queued trigger: {trigger} with args: {args}"
                )  # Debugging
                try:
                    # Use internal fire method that doesn't check firing mode again
                    await self._internal_fire_async(trigger, *args)
                except InvalidTransitionError as e:
                    # Log unmet trigger/guard errors from queue processing
                    print(f"Queued trigger '{trigger}' failed: {e}")
                except Exception as e:
                    # Log other unexpected errors during queued trigger execution
                    print(f"Unexpected error processing queued trigger {trigger}: {e}")
                    # Optionally: break loop or implement retry/dead-letter queue?
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                print("Queue processor cancelled.")  # Debugging
                break  # Exit loop if task is cancelled
            except Exception as e:
                # Error during queue.get() or task_done() ?
                print(f"Error in queue processing loop: {e}")
                # Avoid busy-looping on persistent errors
                await asyncio.sleep(1)

    def _get_representation(
        self, state: StateT
    ) -> StateRepresentation[StateT, TriggerT]:
        """Gets the representation for a state, raising if not found."""
        rep = self._state_representations.get(state)
        if rep is None:
            # Attempt lookup via _get_or_add which might create it if called during config
            # but during firing, it should exist.
            raise ConfigurationError(f"State {state!r} has not been configured.")
        return rep

    def _find_common_ancestor(
        self, s1: Optional[StateRepresentation], s2: Optional[StateRepresentation]
    ) -> Optional[StateRepresentation]:
        """Finds the nearest common ancestor state representation."""
        if s1 is None or s2 is None:
            return None
        if s1.includes(s2.state):
            return s1
        if s2.includes(s1.state):
            return s2

        ancestor = s1.superstate
        while ancestor is not None:
            if ancestor.includes(s2.state):
                return ancestor
            ancestor = ancestor.superstate
        return None  # No common ancestor (shouldn't happen if states are in the same machine)

    def _get_exit_actions(
        self, transition: Transition[StateT, TriggerT]
    ) -> List[Callable[[], Awaitable[None]]]:
        """Gets the stack of exit actions to perform."""
        actions: List[Callable[[], Awaitable[None]]] = []
        source_rep = self._get_representation(transition.source)
        dest_rep = self._get_representation(transition.destination)
        common_ancestor = self._find_common_ancestor(source_rep, dest_rep)

        current = source_rep
        while current is not None and current != common_ancestor:
            # Create closure to capture current state's exit action execution
            rep_to_exit = current
            actions.append(lambda rep=rep_to_exit: rep.exit(transition))  # type: ignore[misc]
            current = current.superstate
        return actions

    def _get_entry_actions(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> List[Callable[[], Awaitable[None]]]:
        """Gets the stack of entry actions to perform."""
        actions: List[Callable[[], Awaitable[None]]] = []
        source_rep = self._get_representation(transition.source)
        dest_rep = self._get_representation(transition.destination)
        common_ancestor = self._find_common_ancestor(source_rep, dest_rep)

        # Build path from common ancestor down to destination
        path: List[StateRepresentation[StateT, TriggerT]] = []
        current = dest_rep
        while current is not None and current != common_ancestor:
            path.append(current)
            current = current.superstate

        # Entry actions execute from superstate down to substate
        for rep_to_enter in reversed(path):
            # Create closure
            actions.append(lambda rep=rep_to_enter: rep.enter(transition, args))  # type: ignore[misc]

        return actions

    def fire(self, trigger: TriggerT, *args: Any) -> None:
        """
        Transition the state machine using the specified trigger and arguments.
        The transition will be attempted synchronously.
        Raises TypeError if the required transition involves async actions or guards.
        Raises InvalidTransitionError if the trigger is not permitted or guards fail.
        """
        if self._firing_mode == FiringMode.QUEUED:
            raise StatelessError(
                "Cannot fire synchronously when FiringMode is QUEUED. Use fire_async."
            )

        # Simple reentrancy check for sync immediate mode
        if self._firing:
            raise InvalidTransitionError(
                f"Reentrant call to 'fire' detected for trigger {trigger!r} from state {self.state!r}. "
                "Synchronous reentrant firing is not allowed. Use async or configure explicit reentry transitions."
            )

        self._firing = True
        try:
            # Run the async internal fire method, but check for async usage within it
            # This requires _internal_fire_async to raise TypeError if async is detected
            # A cleaner way might be a dedicated _internal_fire_sync method.
            # Let's try adapting _internal_fire_async first.
            asyncio.run(self._internal_fire_async(trigger, *args, sync_mode=True))
        finally:
            self._firing = False

    async def fire_async(self, trigger: TriggerT, *args: Any) -> None:
        """
        Transition the state machine using the specified trigger and arguments.
        The transition will be attempted asynchronously, allowing for async guards and actions.
        If FiringMode is QUEUED, the trigger is added to the queue.
        Raises InvalidTransitionError if the trigger is not permitted or guards fail (in IMMEDIATE mode).
        """
        if self._firing_mode == FiringMode.QUEUED and self._queue is not None:
            self._ensure_queue_processor_started()  # Ensure processor is running
            if not self._queue_started:
                # Should we raise an error or just log?
                # Raising might be better as the trigger won't be processed.
                raise RuntimeError(
                    "Cannot queue trigger: Event loop not running or queue processor failed to start."
                )
            await self._queue.put((trigger, args))
        else:
            # Prevent reentrant calls in IMMEDIATE async mode as well? Less critical than sync.
            # For now, allow potential reentrancy in async immediate mode.
            await self._internal_fire_async(trigger, *args, sync_mode=False)

    async def _internal_fire_async(
        self, trigger: TriggerT, *args: Any, sync_mode: bool = False
    ) -> None:
        """Core logic for firing a trigger, handling both sync and async paths."""
        current_state = self.state
        representation = self._get_representation(current_state)

        # Find handler (searches up the hierarchy)
        handler_result = await representation.find_handler_for_trigger(trigger, args)
        handler = handler_result.handler

        if handler is None:
            # No handler found anywhere in the hierarchy
            await self._handle_unmet_trigger(current_state, trigger, args, sync_mode)
            return  # Stop processing

        # Check for async usage in sync mode BEFORE checking guards
        if sync_mode:
            if any(g.method_description.is_async for g in handler.guard.conditions):
                raise TypeError(
                    f"Cannot fire trigger '{trigger!r}' synchronously: Guard '{handler.guard.description_list}' contains async functions."
                )
            # Check handler type for async nature (e.g., dynamic selector, internal action)
            if (
                isinstance(handler, DynamicTriggerBehaviour)
                and handler.destination_func_info.is_async
            ):
                raise TypeError(
                    f"Cannot fire trigger '{trigger!r}' synchronously: Dynamic destination function '{handler.destination_func_info.description}' is async."
                )
            if (
                isinstance(handler, InternalTriggerBehaviour)
                and handler.action_info.is_async
            ):
                raise TypeError(
                    f"Cannot fire trigger '{trigger!r}' synchronously: Internal action '{handler.action_info.description}' is async."
                )
            # Entry/Exit/Activate/Deactivate actions will be checked later if a transition occurs

        # Check guards
        guards_met = await handler.guard.conditions_met_async(args)

        if not guards_met:
            unmet_desc = await handler.guard.unmet_conditions_async(args)
            # Raise specific error for unmet guards
            raise InvalidTransitionError(
                f"Trigger '{trigger!r}' is valid from state {current_state!r} but guard conditions were not met. "
                f"Args: {args}. Unmet guards: {unmet_desc}"
            )

        # --- Guards passed, determine transition ---

        # Handle ignored triggers first
        if isinstance(handler, IgnoredTriggerBehaviour):
            return  # Do nothing further

        destination: Optional[StateT] = None
        is_internal = False
        is_reentry = False

        if isinstance(handler, ReentryTriggerBehaviour):
            destination = handler.destination
            is_reentry = True
        elif isinstance(handler, InternalTriggerBehaviour):
            is_internal = True
            destination = current_state  # Stays in the same state
        elif isinstance(handler, TransitioningTriggerBehaviour):
            destination = handler.destination
        elif isinstance(handler, DynamicTriggerBehaviour):
            destination = await handler._get_destination_async(
                args
            )  # Already handles sync/async selector call
        else:
            # Should not happen if all behaviours are handled
            raise StatelessError(f"Unknown trigger behaviour type: {type(handler)}")

        if destination is None and not is_internal:
            # Should only happen for Ignored or potentially error in Dynamic?
            # Ignored is handled. If Dynamic returns None, treat as error? Or internal?
            # Let's treat None destination from Dynamic as an error for now.
            raise InvalidTransitionError(
                f"Dynamic destination function for trigger '{trigger!r}' returned None."
            )

        # --- Execute Transition ---
        transition = Transition(current_state, destination, trigger, args)

        # Get representation for destination
        dest_representation = self._get_representation(destination)

        with self._lock:  # Protect state mutation and action execution sequence
            if is_internal:
                # Execute internal action only
                internal_handler = cast(InternalTriggerBehaviour, handler)
                # Check action async in sync mode
                if sync_mode and internal_handler.action_info.is_async:
                    raise TypeError(
                        f"Cannot fire trigger '{trigger!r}' synchronously: Internal action '{internal_handler.action_info.description}' is async."
                    )
                await internal_handler.execute_internal_action(transition, args)
            else:
                # --- Standard Transition (including Reentry) ---
                exit_actions = self._get_exit_actions(transition)
                entry_actions = self._get_entry_actions(transition, args)

                # Check actions for async usage in sync mode
                if sync_mode:
                    source_rep = self._get_representation(current_state)
                    common_ancestor = self._find_common_ancestor(
                        source_rep, dest_representation
                    )
                    # Check exit actions
                    curr = source_rep
                    while curr is not None and curr != common_ancestor:
                        if any(a.description.is_async for a in curr.exit_actions):
                            raise TypeError(
                                f"Cannot fire trigger '{trigger!r}' synchronously: Exit action in state {curr.state!r} is async."
                            )
                        if any(a.description.is_async for a in curr.deactivate_actions):
                            raise TypeError(
                                f"Cannot fire trigger '{trigger!r}' synchronously: Deactivate action in state {curr.state!r} is async."
                            )
                        curr = curr.superstate
                    # Check entry actions
                    path: List[StateRepresentation[StateT, TriggerT]] = []
                    curr = dest_representation
                    while curr is not None and curr != common_ancestor:
                        path.append(curr)
                        curr = curr.superstate
                    for rep_to_enter in reversed(path):
                        if any(
                            a.description.is_async for a in rep_to_enter.entry_actions
                        ):
                            raise TypeError(
                                f"Cannot fire trigger '{trigger!r}' synchronously: Entry action in state {rep_to_enter.state!r} is async."
                            )
                        if any(
                            a.description.is_async
                            for a in rep_to_enter.activate_actions
                        ):
                            raise TypeError(
                                f"Cannot fire trigger '{trigger!r}' synchronously: Activate action in state {rep_to_enter.state!r} is async."
                            )

                # Execute exit actions (substate up to common ancestor)
                for action_func in exit_actions:
                    await action_func()

                # Update state
                if self._state_mutator:
                    self._state_mutator(destination)
                else:
                    # Should not happen if using internal state
                    raise RuntimeError("State mutator not configured.")

                # Execute entry actions (common ancestor down to substate)
                for action_func in entry_actions:
                    await action_func()

    async def _handle_unmet_trigger(
        self, state: StateT, trigger: TriggerT, args: Args, sync_mode: bool
    ) -> None:
        """Calls the unmet trigger handler or raises an error."""
        handler_to_call: Optional[
            Union[UnmetTriggerHandler, UnmetTriggerHandlerAsync]
        ] = None
        is_async_handler = False

        if self._unmet_trigger_handler_async:
            handler_to_call = self._unmet_trigger_handler_async
            is_async_handler = True  # Assume it could be async
        elif self._unmet_trigger_handler:
            handler_to_call = self._unmet_trigger_handler
            # Check if the sync handler is actually async (shouldn't be, but check)
            if inspect.iscoroutinefunction(handler_to_call):
                is_async_handler = True

        if handler_to_call:
            if sync_mode and is_async_handler:
                raise TypeError(
                    f"Cannot handle unmet trigger '{trigger!r}' synchronously: Configured handler is async."
                )

            result = handler_to_call(state, trigger, args)
            if inspect.isawaitable(result):
                await result
        else:
            raise InvalidTransitionError(
                f"No valid transitions permitted for trigger '{trigger!r}' from state {state!r}. Args: {args}"
            )

    def can_fire(self, trigger: TriggerT, *args: Any) -> bool:
        """
        Checks if the specified trigger can be fired in the current state (synchronously).
        Raises TypeError if any potential guard is asynchronous.
        """
        current_state = self.state
        representation = self._get_representation(current_state)
        try:
            # Need to synchronously find handler and check guards
            handler, is_async_guard = self._find_handler_sync(representation, trigger)

            if handler is None:
                return False  # No handler found

            if is_async_guard:
                raise TypeError(
                    f"Cannot call can_fire synchronously for trigger '{trigger!r}': involves async guards."
                )

            # Check sync guards
            return handler.guard.conditions_met(args)

        except InvalidTransitionError:  # Raised by conditions_met if args mismatch etc.
            return False
        except TypeError as e:
            # Re-raise TypeError if it's due to async guards
            if "async guards" in str(e):
                raise
            return False  # Other TypeErrors might occur
        except Exception:  # Other errors during check
            return False

    def _find_handler_sync(
        self, representation: StateRepresentation[StateT, TriggerT], trigger: TriggerT
    ) -> Tuple[Optional[TriggerBehaviour[StateT, TriggerT]], bool]:
        """
        Synchronously finds a handler for the trigger, checking for async guards.
        Returns (handler, has_async_guard).
        """
        rep: Optional[StateRepresentation[StateT, TriggerT]] = representation
        while rep is not None:
            behaviours = rep.trigger_behaviours.get(trigger, [])
            if behaviours:  # Found potential handlers at this level
                # Check if *any* guard at this level for this trigger is async
                has_async = any(
                    g.method_description.is_async
                    for b in behaviours
                    for g in b.guard.conditions
                )
                if has_async:
                    # Return the first behaviour found (doesn't matter which) and flag async
                    return behaviours[0], True

                # If no async guards at this level, return the first behaviour
                # The caller (can_fire) will check its sync guards
                return behaviours[0], False

            rep = rep.superstate  # Check superstate

        return None, False  # No handler found

    async def can_fire_async(self, trigger: TriggerT, *args: Any) -> bool:
        """Checks if the specified trigger can be fired in the current state (asynchronously)."""
        current_state = self.state
        representation = self._get_representation(current_state)
        try:
            handler_result = await representation.find_handler_for_trigger(
                trigger, args
            )
            # Check if a handler exists and its guards are met
            return handler_result.guards_met
        except Exception:
            # Errors during guard evaluation mean it can't be fired
            return False

    def get_permitted_triggers(self, *args: Any) -> List[TriggerT]:
        """
        Gets the list of triggers permitted in the current state (synchronous check).
        Skips triggers that have asynchronous guards.
        """
        permitted: List[TriggerT] = []
        current_state = self.state
        representation = self._get_representation(current_state)
        processed_triggers = set()

        rep: Optional[StateRepresentation[StateT, TriggerT]] = representation
        while rep is not None:
            for trigger, behaviours in rep.trigger_behaviours.items():
                if trigger in processed_triggers:
                    continue

                # Check if any behaviour for this trigger at this level has async guards
                has_async_guard = any(
                    g.method_description.is_async
                    for b in behaviours
                    for g in b.guard.conditions
                )
                if has_async_guard:
                    processed_triggers.add(trigger)  # Cannot check synchronously, skip
                    continue

                # Check sync guards for each behaviour
                for behaviour in behaviours:
                    try:
                        guards_met = behaviour.guard.conditions_met(args)
                        if guards_met and not isinstance(
                            behaviour, IgnoredTriggerBehaviour
                        ):
                            permitted.append(trigger)
                            processed_triggers.add(trigger)
                            break  # Found permitted behaviour for this trigger
                        elif guards_met and isinstance(
                            behaviour, IgnoredTriggerBehaviour
                        ):
                            processed_triggers.add(
                                trigger
                            )  # Ignore applies, not permitted
                            break
                    except Exception:
                        # Error during sync guard check means not permitted
                        processed_triggers.add(trigger)
                        break  # Stop checking this trigger at this level
                # If loop finished without break, continue checking superstate for this trigger

            rep = rep.superstate

        return permitted

    async def get_permitted_triggers_async(self, *args: Any) -> List[TriggerT]:
        """Gets the list of triggers permitted in the current state (asynchronous check)."""
        permitted: List[TriggerT] = []
        current_state = self.state
        representation = self._get_representation(current_state)
        processed_triggers = set()

        # Check current state and all superstates
        rep: Optional[StateRepresentation[StateT, TriggerT]] = representation
        while rep is not None:
            for trigger, behaviours in rep.trigger_behaviours.items():
                if trigger in processed_triggers:
                    continue  # Already determined for this trigger in a substate

                for behaviour in behaviours:
                    # Check guards asynchronously
                    try:
                        guards_met = await behaviour.guard.conditions_met_async(args)
                        if guards_met and not isinstance(
                            behaviour, IgnoredTriggerBehaviour
                        ):
                            permitted.append(trigger)
                            processed_triggers.add(trigger)
                            break  # Found a permitted behaviour for this trigger level
                        elif guards_met and isinstance(
                            behaviour, IgnoredTriggerBehaviour
                        ):
                            # If an ignore rule applies, this trigger is not permitted
                            processed_triggers.add(trigger)
                            break
                    except Exception:
                        # Error during guard check means not permitted
                        processed_triggers.add(trigger)
                        break
                # If loop finished without break/adding, continue checking superstate for this trigger
            rep = rep.superstate

        return permitted

    def on_unhandled_trigger(
        self, handler: UnmetTriggerHandler[StateT, TriggerT]
    ) -> None:
        """Registers a synchronous handler for unhandled triggers."""
        self._unmet_trigger_handler = handler

    def on_unhandled_trigger_async(
        self, handler: UnmetTriggerHandlerAsync[StateT, TriggerT]
    ) -> None:
        """Registers an asynchronous handler for unhandled triggers."""
        self._unmet_trigger_handler_async = handler

    def is_in_state(self, state: StateT) -> bool:
        """Checks if the current state is the specified state or one of its substates."""
        current_rep = self._get_representation(self.state)
        return current_rep.is_included_in(state)

    def set_trigger_parameters(self, trigger: TriggerT, *param_types: Type) -> TriggerT:
        """
        Associate parameter types with the specified trigger. This is used for documentation,
        introspection (get_info), and potentially for future validation.

        Args:
            trigger: The trigger to configure.
            *param_types: The types of the parameters the trigger expects.

        Returns:
            The original trigger.
        """
        self._validate_trigger_type(trigger)  # Ensure trigger is hashable etc.
        self._trigger_param_types[trigger] = list(param_types)
        # We return the original trigger, not a wrapper, simplifying the `fire` call.
        return trigger

    def get_info(self) -> "StateMachineInfo":
        """Returns structural information about the state machine configuration."""
        # Imports moved inside to avoid potential circular import issues at module level
        from .trigger_behaviour import (
            IgnoredTriggerBehaviour,
            TransitioningTriggerBehaviour,
            ReentryTriggerBehaviour,
            DynamicTriggerBehaviour,
            InternalTriggerBehaviour,
        )

        state_info_map: Dict[StateT, StateInfo] = {}

        # Pass 1: Create all StateInfo objects without links initially
        for state, rep in self._state_representations.items():
            state_info_map[state] = StateInfo(underlying_state=state)

        # Pass 2: Populate details and links
        for state, rep in self._state_representations.items():
            info = state_info_map[state]

            # Populate actions
            info.entry_actions = [
                ActionInfo(
                    method_description=a.description,
                    from_trigger=getattr(a, "trigger", None),
                )
                for a in rep.entry_actions
            ]
            info.exit_actions = [
                ActionInfo(method_description=a.description) for a in rep.exit_actions
            ]
            info.activate_actions = [
                ActionInfo(method_description=a.description)
                for a in rep.activate_actions
            ]
            info.deactivate_actions = [
                ActionInfo(method_description=a.description)
                for a in rep.deactivate_actions
            ]

            # Populate transitions, ignored, internal, dynamic
            fixed_transitions = []
            ignored_triggers = []
            dynamic_transitions = []
            internal_transitions = []

            for trigger, behaviours in rep.trigger_behaviours.items():
                for behaviour in behaviours:
                    guards = [
                        GuardInfo(method_description=g.method_description)
                        for g in behaviour.guard.conditions
                    ]

                    # Create TriggerInfo with explicit param types if available
                    explicit_params = self._trigger_param_types.get(behaviour.trigger)
                    # TODO: Add inferred signature logic if desired
                    trigger_info = TriggerInfo(
                        underlying_trigger=behaviour.trigger,
                        parameter_types=explicit_params,
                    )

                    if isinstance(behaviour, IgnoredTriggerBehaviour):
                        ignored_triggers.append(
                            IgnoredTransitionInfo(
                                trigger=trigger_info, guard_conditions=guards
                            )
                        )
                    elif isinstance(behaviour, TransitioningTriggerBehaviour):
                        fixed_transitions.append(
                            TransitionInfo(
                                trigger=trigger_info,
                                destination_state=behaviour.destination,
                                guard_conditions=guards,
                            )
                        )
                    elif isinstance(behaviour, ReentryTriggerBehaviour):
                        fixed_transitions.append(
                            TransitionInfo(
                                trigger=trigger_info,
                                destination_state=behaviour.destination,
                                guard_conditions=guards,
                            )
                        )  # Destination is self
                    elif isinstance(behaviour, DynamicTriggerBehaviour):
                        dynamic_transitions.append(
                            DynamicTransitionInfo(
                                trigger=trigger_info,
                                destination_state_selector_description=behaviour.destination_func_info,
                                guard_conditions=guards,
                            )
                        )
                    elif isinstance(behaviour, InternalTriggerBehaviour):
                        # Get action info from the behaviour
                        internal_action_info = ActionInfo(
                            method_description=behaviour.action_info
                        )
                        internal_transitions.append(
                            InternalTransitionInfo(
                                trigger=trigger_info,
                                actions=[
                                    internal_action_info
                                ],  # Assuming one action per internal behaviour for now
                                guard_conditions=guards,
                            )
                        )

            info.fixed_transitions = fixed_transitions
            info.ignored_triggers = ignored_triggers
            info.dynamic_transitions = dynamic_transitions
            info.internal_transitions = internal_transitions  # Assign added list
            info.initial_transition_target = rep.initial_transition_target

            # Link substates using the map
            info.substates = [
                state_info_map[sub_rep.state] for sub_rep in rep.substates
            ]

            # Set superstate value
            if rep.superstate:
                info.superstate_value = rep.superstate.state

        # Determine trigger type (best effort)
        if self._trigger_type is None and self._state_representations:
            first_rep = next(iter(self._state_representations.values()))
            if first_rep.trigger_behaviours:
                first_trigger = next(iter(first_rep.trigger_behaviours.keys()))
                self._trigger_type = type(first_trigger)

        return StateMachineInfo(
            states=list(state_info_map.values()),  # Convert map values to list
            state_type=self._state_type or type(None),
            trigger_type=self._trigger_type or type(None),
            initial_state=self._initial_state,
        )

    def __repr__(self) -> str:
        return f"StateMachine(current_state={self.state!r})"

    # --- Graphing ---
    def generate_dot_graph(self) -> str:
        """Generates a DOT graph representation of the state machine."""
        from .graph import generate_dot_graph  # Local import

        return generate_dot_graph(self.get_info())

    def generate_mermaid_graph(self) -> str:
        """Generates a Mermaid graph representation of the state machine."""
        from .graph import generate_mermaid_graph  # Local import

        return generate_mermaid_graph(self.get_info())

    def visualize(
        self, filename: str = "state_machine.gv", format: str = "png", view: bool = True
    ) -> None:
        """Generates and optionally views a graph using Graphviz."""
        from .graph import visualize_graph  # Local import

        visualize_graph(self, filename, format, view)

    def __del__(self) -> None:
        """Attempt to cleanup queue processor task on deletion."""
        # Note: __del__ is unreliable. Provide an explicit close method if robust cleanup is needed.
        if self._queue_processor_task and not self._queue_processor_task.done():
            print(
                "Attempting to cancel queue processor task in __del__..."
            )  # Debugging
            try:
                # Get loop associated with the task if possible
                loop = self._queue_processor_task.get_loop()
                if loop.is_running():
                    # Schedule cancellation from the loop if it's running
                    loop.call_soon_threadsafe(self._queue_processor_task.cancel)
                    # Give loop a chance to process cancellation? This is tricky in __del__
                else:
                    # If loop isn't running, cancellation might not work as expected
                    self._queue_processor_task.cancel()
            except Exception as e:
                print(
                    f"Error cancelling queue task in __del__: {e}"
                )  # Avoid errors in __del__

    async def close_async(self) -> None:
        """Gracefully shutdown the queue processor if running."""
        if self._queue_processor_task and not self._queue_processor_task.done():
            print("Closing state machine: Cancelling queue processor...")
            self._queue_processor_task.cancel()
            try:
                # Wait for the task to finish cancellation
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass  # Expected exception on cancellation
            except Exception as e:
                print(f"Error during queue processor shutdown: {e}")
            finally:
                self._queue_started = False
                print("Queue processor closed.")
