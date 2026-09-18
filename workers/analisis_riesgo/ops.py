"""Compare observed signal values against rule operators / umbral jsonb."""

from __future__ import annotations

from typing import Any


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def matches(operador: str, observed: Any, umbral: dict[str, Any] | None) -> bool:
    """Return True if the rule condition holds for ``observed``."""
    op = (operador or "").strip().lower()
    threshold = umbral if isinstance(umbral, dict) else {}

    if op == "is_null":
        return observed is None
    if op == "not_null":
        return observed is not None
    if op == "is_true":
        return observed is True
    if op == "is_false":
        return observed is False

    if op in {"eq", "neq"}:
        raw = threshold.get("value", threshold.get("values"))
        if op == "eq":
            return observed == raw
        return observed != raw

    if op in {"in", "not_in"}:
        values = threshold.get("values")
        if not isinstance(values, list):
            single = threshold.get("value")
            values = [single] if single is not None else []
        contained = observed in values
        return contained if op == "in" else not contained

    obs_n = _num(observed)
    if op == "between":
        lo = _num(threshold.get("min"))
        hi = _num(threshold.get("max"))
        if obs_n is None or lo is None or hi is None:
            return False
        return lo <= obs_n <= hi

    bound = _num(threshold.get("value"))
    if obs_n is None or bound is None:
        return False
    if op == "gt":
        return obs_n > bound
    if op == "gte":
        return obs_n >= bound
    if op == "lt":
        return obs_n < bound
    if op == "lte":
        return obs_n <= bound
    return False
