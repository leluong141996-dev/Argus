"""Contract-specific shortcut baselines for `multimodal_matching`.

The shared `generic_baselines()` hard-codes the agent_reasoning stage set
and tag vocabulary, so it does not apply here. multimodal_matching declares
its own full set. Each shortcut returns None for cases where it does not
apply (the gate skips those); the Expectation says how the scorer must
reject it, or -- for oracle -- that it must pass.
"""

from __future__ import annotations

import json
from typing import Any

from baselines.base import Baseline, Expectation
from plugins.multimodal_matching import ontology as O


def _empty_output(case: dict[str, Any]) -> str:
    return ""


def _always_abstain(case: dict[str, Any]) -> str | None:
    # Abstaining is correct on abstain cases -- skip those so this is a
    # genuine shortcut that must fail (on label-required cases).
    if case["expected"]["label"] is O.ABSTAIN:
        return None
    return json.dumps({"label": None})


def _first_label(case: dict[str, Any]) -> str | None:
    first = case["candidates"][0]["label"]
    if first == case["expected"]["label"]:
        return None
    return json.dumps({"label": first})


def _sensitive_label(case: dict[str, Any]) -> str | None:
    expected = case["expected"]["label"]
    sensitive = [c["label"] for c in case["candidates"]
                 if c.get("sensitive") and c["label"] != expected]
    if not sensitive:
        return None
    return json.dumps({"label": sensitive[0]})


def _oracle(case: dict[str, Any]) -> str:
    return json.dumps(case["expected"])


def contract_baselines() -> list[Baseline]:
    return [
        Baseline("empty_output", _empty_output,
                 Expectation(should_pass=False, require_tags=(O.INVALID_JSON,))),
        Baseline("always_abstain", _always_abstain, Expectation(should_pass=False)),
        Baseline("first_label", _first_label, Expectation(should_pass=False)),
        Baseline("sensitive_label", _sensitive_label,
                 Expectation(should_pass=False, require_tags=(O.UNSAFE_MATCH,))),
        Baseline("oracle", _oracle, Expectation(should_pass=True)),
    ]
