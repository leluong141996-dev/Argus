"""Contract-specific shortcut baselines for `query_generation`.

The shared generic_baselines() hard-codes the agent_reasoning stage set, so it
does not apply here. query_generation declares its own full set. Each shortcut
returns None for cases where it does not apply (the gate skips those); the
Expectation says how the scorer must reject it -- or, for oracle, that it must
pass. Baselines run through the deterministic RubricJudge (the plugin's default
in the gate), so the gate stays hermetic and keeps its teeth.
"""

from __future__ import annotations

import json
from typing import Any

from baselines.base import Baseline, Expectation
from core.judge import RubricJudge
from plugins.query_generation import ontology as O


def _empty_output(case: dict[str, Any]) -> str:
    return ""


def _unknown_metric(case: dict[str, Any]) -> str:
    # A well-formed query naming a metric outside the schema. Always a genuine
    # shortcut (ACTION_SELECTION must flag UNKNOWN_FIELD on every case).
    return json.dumps({"metric": "__nope__", "group_by": [], "filters": {}})


def _first_metric(case: dict[str, Any]) -> str | None:
    # Pick the first allowed metric with no filters/groups -- ignores intent.
    metrics = case["schema"].get("metrics", [])
    if not metrics:
        return None
    candidate = {"metric": metrics[0], "group_by": [], "filters": {}}
    # A genuine shortcut only where it misses the intent; skip cases where the
    # rubric is trivially satisfied by metric-only (nothing for REASONING to
    # catch).
    if RubricJudge().grade(rubric=case["rubric"], request=case["request"],
                           query=candidate).passed:
        return None
    return json.dumps(candidate)


def _unsafe_query(case: dict[str, Any]) -> str | None:
    # Oracle query plus a forbidden dimension in group_by. Only applies to
    # cases that declare forbid_dimensions.
    forbid = case.get("constraints", {}).get("forbid_dimensions", [])
    if not forbid:
        return None
    q = dict(case["expected"]["query"])
    q["group_by"] = list(q.get("group_by", [])) + [forbid[0]]
    return json.dumps(q)


def _oracle(case: dict[str, Any]) -> str:
    return json.dumps(case["expected"]["query"])


def contract_baselines() -> list[Baseline]:
    return [
        Baseline("empty_output", _empty_output,
                 Expectation(should_pass=False, require_tags=(O.INVALID_JSON,))),
        Baseline("unknown_metric", _unknown_metric,
                 Expectation(should_pass=False, require_tags=(O.UNKNOWN_FIELD,))),
        Baseline("first_metric", _first_metric,
                 Expectation(should_pass=False, require_tags=(O.INTENT_MISMATCH,))),
        Baseline("unsafe_query", _unsafe_query,
                 Expectation(should_pass=False, require_tags=(O.UNSAFE_QUERY,))),
        Baseline("oracle", _oracle, Expectation(should_pass=True)),
    ]
