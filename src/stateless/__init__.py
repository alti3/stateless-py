"""
Stateless-py: A simple library for creating state machines in Python code.
"""

__version__ = "0.1.0"

from .state_machine import StateMachine
from .state_configuration import StateConfiguration  # Assuming this will exist
from .transition import Transition, StateT, TriggerT
from .exceptions import StatelessError, InvalidTransitionError, ConfigurationError
from .firing_modes import FiringMode

__all__ = [
    "StateMachine",
    "StateConfiguration",
    "Transition",
    "StateT",
    "TriggerT",
    "StatelessError",
    "InvalidTransitionError",
    "ConfigurationError",
    "FiringMode",
    "__version__",
]
