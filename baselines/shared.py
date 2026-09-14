"""Generic, case-agnostic shortcut baselines.

These do not need any task ontology — they are the same broken shapes for
every task: nothing, an empty object, and a valid-JSON no-op answer. Each is
still scored by the real plugin scorer; the Expectation says how the scorer
must reject it.
"""

from __future__ import annotations

import json
from typing import Any

from baselines.base import Baseline, Expectation
from core.pipeline import Stage


def _empty_output(case: dict[str, Any]) -> str:
    return ""


def _schema_only(case: dict[str, Any]) -> str:
    return "{}"


def _no_op(case: dict[str, Any]) -> str:
    return json.dumps(
        {"claims": {}, "evidence_ids": [], "confidence": 0.0, "action": "no_action"}
    )


def generic_baselines() -> list[Baseline]:
    return [
        Baseline(
            "empty_output",
            _empty_output,
            Expectation(should_pass=False, capped_by=Stage.RETRIEVAL, require_tags=("invalid_json",)),
        ),
        Baseline(
            "schema_only",
            _schema_only,
            Expectation(should_pass=False, capped_by=Stage.RETRIEVAL, require_tags=("no_evidence_cited",)),
        ),
        # no_op: valid JSON but empty. Both retrieval (no_evidence_cited) and
        # reasoning (invalid_ontology_value) fail; retrieval is the cap. Do not
        # over-specify the cap — assert only that it fails.
        Baseline("no_op", _no_op, Expectation(should_pass=False)),
    ]
