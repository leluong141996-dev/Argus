"""Canary gate: score each canary's FIXED output and assert the scorer's
verdict still matches the recorded expectation. Catches scorer/harness
regressions on known-answer cases.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from baselines.base import Expectation
from core.pipeline import Stage
from core.runner import RunConfig, run_case
from gates.base import CheckResult, GateResult, match_expectation
from plugins.base import TaskPlugin


def _expectation_from_dict(d: dict[str, Any]) -> Expectation:
    cap = d.get("capped_by")
    return Expectation(
        should_pass=bool(d["should_pass"]),
        capped_by=Stage(cap) if cap else None,
        require_tags=tuple(d.get("require_tags", ())),
    )


def run_canary_gate(
    plugin: TaskPlugin, canary_cases: list[dict[str, Any]], run_config: RunConfig
) -> GateResult:
    checks: list[CheckResult] = []
    for case in canary_cases:
        canary = case.get("_canary")
        if not canary:
            continue
        out = json.dumps(canary["output"])
        rc = replace(run_config, model=f"canary:{case['case_id']}")
        model_call = lambda prompt, _o=out: _o  # noqa: E731
        rec = run_case(plugin, case, model_call, rc)
        ok, detail = match_expectation(rec, _expectation_from_dict(canary["expect"]))
        checks.append(CheckResult(case["case_id"], ok, detail))
    return GateResult("canary", checks)
