"""Exceptions for Hydrocapt."""
from typing import Any


class HydrocaptError(Exception):
    """HydrocaptError from hydrocapt api."""

    def __init__(self, *args: Any) -> None:
        """Initialize the exception.

        Args:
            args: the message or root cause of the error
        """
        Exception.__init__(self, *args)
