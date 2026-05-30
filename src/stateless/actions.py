import inspect
from typing import Any, Generic, cast
from abc import ABC, abstractmethod
from collections.abc import Sequence, Callable, Awaitable

from .reflection import InvocationInfo, ActionDef
from .transition import Transition, StateT, TriggerT
from .exceptions import ConfigurationError

Args = Sequence[Any]
ActionFuncResult = None | Awaitable[None]
ActionFunc = Callable[..., ActionFuncResult]


# --- Base Action Behaviour ---
class ActionBehaviour(ABC, Generic[StateT, TriggerT]):
    """Base class for all action behaviours (entry, exit, activate, deactivate)."""

    def __init__(self, description: InvocationInfo):
        self._description = description

    @property
    def description(self) -> InvocationInfo:
        """Detailed information about the action function."""
        return self._description

    @abstractmethod
    def execute(self, *args: Any) -> None:
        """Executes the action synchronously."""
        pass

    @abstractmethod
    async def execute_async(self, *args: Any) -> None:
        """Executes the action, allowing for async actions."""
        pass


# --- Entry Action ---
class EntryActionBehaviour(ActionBehaviour[StateT, TriggerT]):
    """Base for actions executed when entering a state."""

    @abstractmethod
    def execute(self, transition: Transition[StateT, TriggerT], args: Args) -> None:  # type: ignore[override]
        pass

    @abstractmethod
    async def execute_async(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> None:  # type: ignore[override]
        pass


class SyncEntryAction(EntryActionBehaviour[StateT, TriggerT]):
    """Synchronous entry action."""

    def __init__(
        self,
        action: Callable[[Transition[StateT, TriggerT], Args], None],
        description: InvocationInfo,
    ):
        super().__init__(description)
        self._action = action

    def execute(self, transition: Transition[StateT, TriggerT], args: Args) -> None:
        self._action(transition, args)

    async def execute_async(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> None:
        self.execute(transition, args)  # Execute sync action directly


class AsyncEntryAction(EntryActionBehaviour[StateT, TriggerT]):
    """Asynchronous entry action."""

    def __init__(
        self,
        action: Callable[[Transition[StateT, TriggerT], Args], Awaitable[None]],
        description: InvocationInfo,
    ):
        super().__init__(description)
        self._action = action

    def execute(self, transition: Transition[StateT, TriggerT], args: Args) -> None:
        raise TypeError(
            f"Cannot execute async entry action '{self.description.method_name or '<lambda>'}' synchronously."
        )

    async def execute_async(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> None:
        await self._action(transition, args)


class EntryActionBehaviorFromTrigger(EntryActionBehaviour[StateT, TriggerT]):
    """Entry action that only executes if the transition was caused by a specific trigger."""

    def __init__(
        self,
        trigger: TriggerT,
        action_behaviour: EntryActionBehaviour[StateT, TriggerT],
    ):
        # Use the inner action's description, but perhaps add context?
        desc = f"{action_behaviour.description.description} (when triggered by {trigger!r})"
        inv_info = InvocationInfo(
            method_name=action_behaviour.description.method_name,
            description=desc,
            is_async=action_behaviour.description.is_async,
        )
        super().__init__(inv_info)
        self._trigger = trigger
        self._action_behaviour = action_behaviour

    @property
    def trigger(self) -> TriggerT:
        """The specific trigger required for this action to execute."""
        return self._trigger

    def execute(self, transition: Transition[StateT, TriggerT], args: Args) -> None:
        if transition.trigger == self._trigger:
            self._action_behaviour.execute(transition, args)

    async def execute_async(
        self, transition: Transition[StateT, TriggerT], args: Args
    ) -> None:
        if transition.trigger == self._trigger:
            await self._action_behaviour.execute_async(transition, args)


# --- Exit Action ---
class ExitActionBehaviour(ActionBehaviour[StateT, TriggerT]):
    """Base for actions executed when exiting a state."""

    # Exit actions in C# only take Transition, not args
    @abstractmethod
    def execute(self, transition: Transition[StateT, TriggerT]) -> None:  # type: ignore[override]
        pass

    @abstractmethod
    async def execute_async(self, transition: Transition[StateT, TriggerT]) -> None:  # type: ignore[override]
        pass


class SyncExitAction(ExitActionBehaviour[StateT, TriggerT]):
    """Synchronous exit action."""

    def __init__(
        self,
        action: Callable[[Transition[StateT, TriggerT]], None],
        description: InvocationInfo,
    ):
        super().__init__(description)
        self._action = action

    def execute(self, transition: Transition[StateT, TriggerT]) -> None:
        self._action(transition)

    async def execute_async(self, transition: Transition[StateT, TriggerT]) -> None:
        self.execute(transition)


class AsyncExitAction(ExitActionBehaviour[StateT, TriggerT]):
    """Asynchronous exit action."""

    def __init__(
        self,
        action: Callable[[Transition[StateT, TriggerT]], Awaitable[None]],
        description: InvocationInfo,
    ):
        super().__init__(description)
        self._action = action

    def execute(self, transition: Transition[StateT, TriggerT]) -> None:
        raise TypeError(
            f"Cannot execute async exit action '{self.description.method_name or '<lambda>'}' synchronously."
        )

    async def execute_async(self, transition: Transition[StateT, TriggerT]) -> None:
        await self._action(transition)


# --- Activate / Deactivate Actions (simplified, no args) ---
class ActivateActionBehaviour(ActionBehaviour[StateT, TriggerT]):
    """Base for actions executed when a state is activated."""

    @abstractmethod
    def execute(self) -> None:  # type: ignore[override]
        pass

    @abstractmethod
    async def execute_async(self) -> None:  # type: ignore[override]
        pass


class SyncActivateAction(ActivateActionBehaviour[StateT, TriggerT]):
    """Synchronous activate action."""

    def __init__(self, action: Callable[[], None], description: InvocationInfo):
        super().__init__(description)
        self._action = action

    def execute(self) -> None:
        self._action()

    async def execute_async(self) -> None:
        self.execute()


class AsyncActivateAction(ActivateActionBehaviour[StateT, TriggerT]):
    """Asynchronous activate action."""

    def __init__(
        self, action: Callable[[], Awaitable[None]], description: InvocationInfo
    ):
        super().__init__(description)
        self._action = action

    def execute(self) -> None:
        raise TypeError("Cannot execute async activate action synchronously.")

    async def execute_async(self) -> None:
        await self._action()


class DeactivateActionBehaviour(ActionBehaviour[StateT, TriggerT]):
    """Base for actions executed when a state is deactivated."""

    @abstractmethod
    def execute(self) -> None:
        pass  # type: ignore[override]

    @abstractmethod
    async def execute_async(self) -> None:
        pass  # type: ignore[override]


class SyncDeactivateAction(DeactivateActionBehaviour[StateT, TriggerT]):
    """Synchronous deactivate action."""

    def __init__(self, action: Callable[[], None], description: InvocationInfo):
        super().__init__(description)
        self._action = action

    def execute(self) -> None:
        self._action()

    async def execute_async(self) -> None:
        self.execute()


class AsyncDeactivateAction(DeactivateActionBehaviour[StateT, TriggerT]):
    """Asynchronous deactivate action."""

    def __init__(
        self, action: Callable[[], Awaitable[None]], description: InvocationInfo
    ):
        super().__init__(description)
        self._action = action

    def execute(self) -> None:
        raise TypeError("Cannot execute async deactivate action synchronously.")

    async def execute_async(self) -> None:
        await self._action()


# --- Parameter Conversion and Factory Helpers ---


def _get_action_and_description(
    action_def: ActionDef,
) -> tuple[Callable, str | None]:
    """Extracts the callable and optional description from ActionDef."""
    if isinstance(action_def, tuple):
        if (
            len(action_def) == 2
            and callable(action_def[0])
            and isinstance(action_def[1], (str, type(None)))
        ):
            return action_def[0], action_def[1]
        else:
            raise ValueError(
                "Invalid ActionDef tuple format. Expected (callable, Optional[str])."
            )
    elif callable(action_def):
        return action_def, None
    else:
        raise TypeError(
            "Action definition must be a callable or a (callable, description) tuple."
        )


def _build_wrapper(
    action: Callable, expected_args: list[str], is_async: bool
) -> Callable[..., ActionFuncResult]:
    """Builds a wrapper function to adapt the user's action callable to the expected signature."""
    sig = inspect.signature(action)
    params = list(sig.parameters.values())
    has_varargs = any(p.kind == p.VAR_POSITIONAL for p in params)
    has_varkw = any(p.kind == p.VAR_KEYWORD for p in params)
    positional_params = [
        p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    ]
    required_keyword_only = [
        p
        for p in params
        if p.kind == p.KEYWORD_ONLY and p.default == inspect.Parameter.empty
    ]

    action_name = getattr(action, "__name__", "<lambda>")
    if has_varkw and not positional_params and not has_varargs:
        raise ConfigurationError(
            f"Action '{action_name}' signature {sig} is incompatible: **kwargs-only actions are not supported."
        )
    if required_keyword_only:
        raise ConfigurationError(
            f"Action '{action_name}' signature {sig} is incompatible: required keyword-only parameters are not supported."
        )

    context_names = set(expected_args)
    private_context_names = {f"_{name}": name for name in expected_args}

    def build_call_args(all_args: tuple[Any, ...]) -> list[Any]:
        context = dict(zip(expected_args, all_args, strict=False))
        trigger_args = tuple(context.get("args", ()))

        if has_varargs:
            if expected_args == ["args"]:
                return list(trigger_args)
            return list(all_args)

        call_args: list[Any] = []
        next_trigger_arg = 0
        fallback_context = iter(all_args)

        for param in positional_params:
            if param.name in context_names:
                value = context[param.name]
            elif param.name in private_context_names:
                value = context[private_context_names[param.name]]
            elif "transition" in context and len(positional_params) == 1:
                value = context["transition"]
            elif not context and len(positional_params) == 1:
                value = None
            elif next_trigger_arg < len(trigger_args):
                value = trigger_args[next_trigger_arg]
                next_trigger_arg += 1
            else:
                try:
                    value = next(fallback_context)
                except StopIteration:
                    if param.default != inspect.Parameter.empty:
                        continue
                    raise ConfigurationError(
                        f"Action '{action_name}' signature {sig} is incompatible with the supplied arguments."
                    ) from None
            call_args.append(value)

        return call_args

    if is_async:

        async def async_wrapper(*all_args: Any) -> None:
            return await action(*build_call_args(all_args))

        return async_wrapper

    def sync_wrapper(*all_args: Any) -> None:
        return action(*build_call_args(all_args))

    return sync_wrapper


def create_entry_action_behavior(
    action_def: ActionDef, trigger: TriggerT | None = None
) -> EntryActionBehaviour[StateT, TriggerT]:
    """Factory to create sync/async entry action behaviors."""
    action, description_override = _get_action_and_description(action_def)
    invocation_info = InvocationInfo.from_callable(action, description_override)
    is_async = invocation_info.is_async

    # Entry actions expect (transition, args_tuple)
    wrapped_action = _build_wrapper(action, ["transition", "args"], is_async)

    action_behavior: EntryActionBehaviour[StateT, TriggerT]
    if is_async:
        # Cast needed because _build_wrapper returns a generic callable
        async_wrapped = cast(
            Callable[[Transition[StateT, TriggerT], Args], Awaitable[None]],
            wrapped_action,
        )
        action_behavior = AsyncEntryAction(async_wrapped, invocation_info)
    else:
        sync_wrapped = cast(
            Callable[[Transition[StateT, TriggerT], Args], None], wrapped_action
        )
        action_behavior = SyncEntryAction(sync_wrapped, invocation_info)

    if trigger is not None:
        action_behavior = EntryActionBehaviorFromTrigger[StateT, TriggerT](
            trigger, action_behavior
        )

    return action_behavior


def create_exit_action_behavior(
    action_def: ActionDef,
) -> ExitActionBehaviour[StateT, TriggerT]:
    """Factory to create sync/async exit action behaviors."""
    action, description_override = _get_action_and_description(action_def)
    invocation_info = InvocationInfo.from_callable(action, description_override)
    is_async = invocation_info.is_async

    # Exit actions expect only (transition)
    wrapped_action = _build_wrapper(action, ["transition"], is_async)

    if is_async:
        async_wrapped = cast(
            Callable[[Transition[StateT, TriggerT]], Awaitable[None]], wrapped_action
        )
        return AsyncExitAction(async_wrapped, invocation_info)
    else:
        sync_wrapped = cast(
            Callable[[Transition[StateT, TriggerT]], None], wrapped_action
        )
        return SyncExitAction(sync_wrapped, invocation_info)


def create_activate_action_behavior(
    action_def: ActionDef,
) -> ActivateActionBehaviour[StateT, TriggerT]:
    """Factory to create sync/async activate action behaviors."""
    action, description_override = _get_action_and_description(action_def)
    invocation_info = InvocationInfo.from_callable(action, description_override)
    is_async = invocation_info.is_async

    # Activate actions expect no arguments
    wrapped_action = _build_wrapper(action, [], is_async)

    if is_async:
        async_wrapped = cast(Callable[[], Awaitable[None]], wrapped_action)
        return AsyncActivateAction(async_wrapped, invocation_info)
    else:
        sync_wrapped = cast(Callable[[], None], wrapped_action)
        return SyncActivateAction(sync_wrapped, invocation_info)


def create_deactivate_action_behavior(
    action_def: ActionDef,
) -> DeactivateActionBehaviour[StateT, TriggerT]:
    """Factory to create sync/async deactivate action behaviors."""
    action, description_override = _get_action_and_description(action_def)
    invocation_info = InvocationInfo.from_callable(action, description_override)
    is_async = invocation_info.is_async

    # Deactivate actions expect no arguments
    wrapped_action = _build_wrapper(action, [], is_async)

    if is_async:
        async_wrapped = cast(Callable[[], Awaitable[None]], wrapped_action)
        return AsyncDeactivateAction(async_wrapped, invocation_info)
    else:
        sync_wrapped = cast(Callable[[], None], wrapped_action)
        return SyncDeactivateAction(sync_wrapped, invocation_info)
