"""Process errors and their exit codes."""

from __future__ import annotations


class DataPoisonError(Exception):
    """Operational error with a stable process exit code."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


class UsageError(DataPoisonError):
    """Invalid arguments or configuration. Exit 2."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 2)


class InputError(DataPoisonError):
    """Input, parse, or validation failure. Exit 3."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 3)


class LimitError(DataPoisonError):
    """A safety ceiling was exceeded. Exit 4."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 4)


class IntegrityError(DataPoisonError):
    """Replay or hash verification failed. Exit 6."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 6)
