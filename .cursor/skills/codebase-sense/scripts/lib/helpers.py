from __future__ import annotations

from typing import Any


def as_int(value: object, default: int) -> int:
    """Coerce a value to int with fallback. Handles bool, int, float, str."""
    converters: dict[type, Any] = {
        bool: lambda v: int(v),
        int: lambda v: v,
        float: lambda v: int(v),
    }
    converter = converters.get(type(value))
    if converter is not None:
        return converter(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def classify(value: float, thresholds: list[tuple[float, str]], default: str) -> str:
    """Classify a value against sorted descending thresholds.

    thresholds is a list of (min_value, label) sorted descending by min_value.
    Returns the label for the first threshold where value >= min_value.
    """
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return default
