"""Resolve senales.json_path values from analisis-v1 with agregacion semantics."""

from __future__ import annotations

from typing import Any


def _split_path(path: str) -> list[str]:
    return [p for p in (path or "").split(".") if p]


def get_by_path(root: Any, path: str) -> Any:
    """Walk a dotted path; ``[]`` segments are not expanded here."""
    cur = root
    for part in _split_path(path):
        if part.endswith("[]"):
            part = part[:-2]
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _array_leaf_path(json_path: str) -> tuple[str, str] | None:
    """Split ``modules.origins.per_chain[].x.y`` into (array_path, leaf_path)."""
    marker = "[]."
    if marker not in (json_path or ""):
        return None
    head, leaf = json_path.split(marker, 1)
    # head may end with ``per_chain`` or ``hops`` (without [])
    array_path = head.replace("[]", "")
    return array_path, leaf


def collect_values(analisis: dict[str, Any], json_path: str, agregacion: str) -> list[Any]:
    """
    Return candidate values for a signal.

    - aggregate / root: single value (list length 1, may be None)
    - per_chain / hop: one value per array element; rule matches if ANY matches
    """
    agg = (agregacion or "aggregate").strip().lower()
    if agg in {"aggregate", "root"}:
        path = (json_path or "").replace("[]", "")
        return [get_by_path(analisis, path)]

    split = _array_leaf_path(json_path)
    if split is None:
        return [get_by_path(analisis, (json_path or "").replace("[]", ""))]

    array_path, leaf = split
    arr = get_by_path(analisis, array_path)
    if not isinstance(arr, list):
        return []
    out: list[Any] = []
    for item in arr:
        if not isinstance(item, dict):
            out.append(None)
            continue
        out.append(get_by_path(item, leaf))
    return out


def primary_value(values: list[Any]) -> Any:
    """Representative observed value for the envelope (first non-null, else None)."""
    for v in values:
        if v is not None:
            return v
    return None if values else None
