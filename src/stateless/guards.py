import inspect
from typing import (
    Any,
    Generic,
    TypeVar,
)
from collections.abc import Sequence, Callable, Awaitable

# Assuming reflection models are defined in reflection.py
from .reflection import InvocationInfo, GuardDef

T = TypeVar("T")
GuardResult = bool | Awaitable[bool]


class GuardCondition(Generic[T]):
    """Represents a single guard condition function."""

    def __init__(
        self, method: Callable[..., GuardResult], description: str | None = None
    ):
        if not callable(method):
            raise TypeError("Guard method must be callable.")
        self._method = method
        self._invocation_info = InvocationInfo.from_callable(method, description)

    @property
    def method(self) -> Callable[..., GuardResult]:
        """The guard function."""
        return self._method

    @property
    def description(self) -> str:
        """A description of the guard."""
        return self._invocation_info.description

    @property
    def method_description(self) -> InvocationInfo:
        """Detailed information about the guard function."""
        return self._invocation_info

    def _check_args(self, args: Sequence[Any]) -> tuple[bool, Sequence[Any]]:
        """Determines if the guard can be called with args and returns the relevant slice."""
        try:
            sig = inspect.signature(self._method)
            num_params = len(sig.parameters)
            # Check for *args parameter
            has_varargs = any(
                p.kind == p.VAR_POSITIONAL for p in sig.parameters.values()
            )

            if has_varargs:
                return True, args  # Pass all args if *args is present
            elif num_params == 0:
                return True, ()
            elif num_params <= len(args):
                return True, args[:num_params]
            else:  # Not enough arguments provided for the guard
                return False, ()
        except ValueError:  # inspect.signature can fail on some built-ins/C functions
            # Assume it takes no args if signature fails? Or re-raise?
            # Let's assume it might work with provided args or no args.
            # This is a simplification. A more robust solution might be needed.
            if len(args) > 0:
                return True, args  # Try passing args
            else:
                return True, ()  # Try passing no args

    def is_met(self, args: Sequence[Any]) -> bool:
        """
        Evaluates the guard condition synchronously.
        Raises TypeError if the guard is async.
        """
        if self._invocation_info.is_async:
            raise TypeError(
                f"Cannot call async guard '{self.description}' synchronously. Use is_met_async."
            )

        can_call, call_args = self._check_args(args)
        if not can_call:
            return False  # Should ideally raise, but C# seems to return false if args mismatch

        try:
            result = self._method(*call_args)
            if inspect.isawaitable(
                result
            ):  # Double check, shouldn't happen if is_async is False
                raise TypeError(
                    f"Guard '{self.description}' returned an awaitable but was not marked async."
                )
            return bool(result)
        except Exception:
            # C# lets guard exceptions bubble up. Let's follow that.
            raise

    async def is_met_async(self, args: Sequence[Any]) -> bool:
        """Evaluates the guard condition, allowing for async guards."""
        can_call, call_args = self._check_args(args)
        if not can_call:
            return False

        try:
            result = self._method(*call_args)
            if inspect.isawaitable(result):
                return bool(await result)
            else:
                return bool(
                    result
                )  # Ensure result is boolean even for sync guards called via async path
        except Exception:
            raise


class TransitionGuard:
    """Represents a collection of guard conditions for a transition."""

    def __init__(self, conditions: Sequence[GuardCondition]):
        self._conditions = tuple(conditions)  # Immutable sequence

    @property
    def conditions(self) -> tuple[GuardCondition, ...]:
        """The guard conditions associated with this transition."""
        return self._conditions

    @property
    def description_list(self) -> list[str]:
        """A list of descriptions for all guard conditions."""
        return [c.description for c in self._conditions]

    @classmethod
    def from_definitions(cls, guards: Sequence[GuardDef]) -> "TransitionGuard":
        """Creates a TransitionGuard from a sequence of (callable, description) tuples."""
        return cls([GuardCondition(g, d) for g, d in guards])

    def conditions_met(self, args: Sequence[Any]) -> bool:
        """
        Checks if all synchronous guard conditions are met.
        Raises TypeError if any guard is async.
        """
        if any(c.method_description.is_async for c in self._conditions):
            raise TypeError(
                "Cannot evaluate guards synchronously when async guards are present. Use conditions_met_async."
            )
        return all(c.is_met(args) for c in self._conditions)

    async def conditions_met_async(self, args: Sequence[Any]) -> bool:
        """Checks if all guard conditions (sync and async) are met."""
        # Run sequentially for simplicity. Could potentially run concurrently.
        for condition in self._conditions:
            if not await condition.is_met_async(args):
                return False
        return True

    def unmet_conditions(self, args: Sequence[Any]) -> list[str]:
        """
        Returns descriptions of unmet synchronous guard conditions.
        Raises TypeError if any guard is async.
        """
        if any(c.method_description.is_async for c in self._conditions):
            raise TypeError(
                "Cannot evaluate unmet conditions synchronously when async guards are present. Use unmet_conditions_async."
            )
        return [c.description for c in self._conditions if not c.is_met(args)]

    async def unmet_conditions_async(self, args: Sequence[Any]) -> list[str]:
        """Returns descriptions of unmet guard conditions (sync and async)."""
        unmet = []
        for condition in self._conditions:
            is_met = await condition.is_met_async(args)
            if not is_met:
                unmet.append(condition.description)
        return unmet


# Singleton for no guards
EMPTY_GUARD = TransitionGuard([])


# Helper function (might be redundant with from_definitions)
def guards_from_definitions(definitions: Sequence[GuardDef]) -> TransitionGuard:
    """Creates a TransitionGuard from a sequence of (callable, description) tuples."""
    if not definitions:
        return EMPTY_GUARD
    return TransitionGuard.from_definitions(definitions)
