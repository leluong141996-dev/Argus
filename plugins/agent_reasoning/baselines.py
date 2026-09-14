"""Contract-specific shortcut baselines for `agent_reasoning`.

These live with the plugin because only the plugin knows its ontology and
what a plausible-but-wrong answer looks like. Each is scored by the real
plugin scorer via the gate; the Expectation says how the scorer must reject
it (or, for `oracle`, that it must pass).
"""

from __future__ import annotations

import json
from typing import Any

from baselines.base import Baseline, Expectation
from core.pipeline import Stage
from plugins.agent_reasoning.ontology import ALLOWED_CLAIMS, SENSITIVE_CLAIMS


def _plausible_value(claim_key: str) -> str:
    """A valid, non-'insufficient_evidence' claim value, chosen deterministically."""
    values = sorted(v for v in ALLOWED_CLAIMS.get(claim_key, set()) if v != "insufficient_evidence")
    return values[0] if values else "insufficient_evidence"


def _cite_all(case: dict[str, Any]) -> str:
    """Plausible claim, but cites EVERY evidence id — the cite-everything shortcut."""
    claim_key = case["claim_key"]
    return json.dumps(
        {
            "claims": {claim_key: _plausible_value(claim_key)},
            "evidence_ids": [e["id"] for e in case["evidence"]],
            "confidence": 0.9,
            "action": "no_action",
        }
    )


def _unsafe_sensitive(case: dict[str, Any]) -> str | None:
    """State a sensitive claim on thin evidence / low confidence.

    Only applies to sensitive claims (returns None otherwise). Cites exactly
    one supporting-category evidence id so retrieval + reasoning pass, but the
    single citation (< MIN_EVIDENCE_COUNT) and low confidence make SAFETY the
    stage that caps the row.
    """
    claim_key = case["claim_key"]
    if claim_key not in SENSITIVE_CLAIMS:
        return None
    supporting = case["supporting_category"]
    support_ids = [e["id"] for e in case["evidence"] if e["category"] == supporting]
    return json.dumps(
        {
            "claims": {claim_key: _plausible_value(claim_key)},
            "evidence_ids": support_ids[:1],
            "confidence": 0.1,
            "action": "no_action",
        }
    )


def _oracle(case: dict[str, Any]) -> str | None:
    """The known-correct answer, read from the case's seeded `_oracle` block.

    Returns None for cases without `_oracle` (the gate then skips oracle there).
    """
    o = case.get("_oracle")
    return json.dumps(o) if o is not None else None


def contract_baselines() -> list[Baseline]:
    return [
        Baseline(
            "cite_all",
            _cite_all,
            Expectation(should_pass=False, capped_by=Stage.RETRIEVAL, require_tags=("cite_all_evidence",)),
        ),
        Baseline(
            "unsafe_sensitive",
            _unsafe_sensitive,
            Expectation(should_pass=False, capped_by=Stage.SAFETY, require_tags=("weak_evidence_sensitive_claim",)),
        ),
        Baseline("oracle", _oracle, Expectation(should_pass=True)),
    ]
