"""Portable gameplay saves, independent of either client."""

from .saves import MAX_SAVE_BYTES, dumps, loads

__all__ = ["MAX_SAVE_BYTES", "dumps", "loads"]
