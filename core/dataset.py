"""Loads evaluation cases from a JSON file: {"task": ..., "cases": [ {...} ]}."""
from __future__ import annotations

import json
import os
from typing import Any


class DatasetError(Exception):
    pass


KNOWN_SPLITS: tuple[str, ...] = ("teaching", "certification", "canary")


def split_of(path: str) -> str | None:
    """Return the dataset split a path belongs to, or None.

    The split is the path segment immediately following a 'datasets'
    segment, but only if it is one of KNOWN_SPLITS. Paths not shaped like
    datasets/<known-split>/... (tmp fixtures, ad-hoc files) return None;
    the loader stays permissive and only require_split turns a mismatch
    into an error.
    """
    parts = os.path.normpath(path).split(os.sep)
    for i, seg in enumerate(parts):
        if seg == "datasets" and i + 1 < len(parts):
            nxt = parts[i + 1]
            return nxt if nxt in KNOWN_SPLITS else None
    return None


def load_cases(path: str) -> list[dict[str, Any]]:
    try:
        with open(path) as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise DatasetError(f"dataset file not found: {path}") from None
    except json.JSONDecodeError as e:
        raise DatasetError(f"invalid JSON in {path}: {e}") from e

    cases = raw.get("cases") if isinstance(raw, dict) else None
    if not isinstance(cases, list) or not cases:
        raise DatasetError(f"{path} must contain a non-empty 'cases' list")
    for i, c in enumerate(cases):
        if not isinstance(c, dict) or "case_id" not in c:
            raise DatasetError(f"case #{i} in {path} is missing 'case_id'")
    return cases
