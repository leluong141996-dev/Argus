"""Write RowRecords to a JSON report file and read it back."""
from __future__ import annotations

import json
import os
from typing import Any

from core.record_schema import RowRecord


def write_records(records: list[RowRecord], path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        json.dump([r.to_dict() for r in records], f, indent=2)


def read_records(path: str) -> list[dict[str, Any]]:
    with open(path) as f:
        return json.load(f)
