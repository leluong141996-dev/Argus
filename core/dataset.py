"""Loads evaluation cases from a JSON file: {"task": ..., "cases": [ {...} ]}."""
from __future__ import annotations

import json
from typing import Any


class DatasetError(Exception):
    pass


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
