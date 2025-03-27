from enum import Enum, auto


class FiringMode(Enum):
    """Specifies how triggers are processed when fired."""

    IMMEDIATE = auto()
    """Triggers are processed immediately when fired."""
    QUEUED = auto()
    """Triggers are added to a queue and processed sequentially."""
