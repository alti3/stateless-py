# src/stateless/exceptions.py
class StatelessError(Exception):
    """Base class for Stateless exceptions."""

    pass


class InvalidTransitionError(StatelessError, ValueError):
    """Error raised when a transition is attempted but not permitted."""

    pass


class ConfigurationError(StatelessError, ValueError):
    """Error raised during state machine configuration."""

    pass
