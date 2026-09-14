"""Baseline gate: run each shortcut baseline through the REAL scorer and
assert every produced row matches the baseline's Expectation.

No scoring logic here — it wraps each case's fake output in a per-case model
call and hands it to the existing core.runner.run_case.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from baselines.base import Baseline
from core.record_schema import RowRecord
from core.runner import RunConfig, run_case
from gates.base import CheckResult, GateResult, match_expectation
from plugins.base import TaskPlugin


def _run_baseline_over_cases(
    plugin: TaskPlugin, baseline: Baseline, cases: list[dict[str, Any]], run_config: RunConfig
) -> list[RowRecord]:
    rc = replace(run_config, model=f"baseline:{baseline.name}")
    records: list[RowRecord] = []
    for case in cases:
        out = baseline.build_output(case)
        if out is None:  # baseline does not apply to this case
            continue
        model_call = lambda prompt, _o=out: _o  # noqa: E731 - bound per iteration
        records.append(run_case(plugin, case, model_call, rc))
    return records


def run_baseline_gate(
    plugin: TaskPlugin, cases: list[dict[str, Any]], run_config: RunConfig
) -> GateResult:
    checks: list[CheckResult] = []
    for baseline in plugin.baselines():
        records = _run_baseline_over_cases(plugin, baseline, cases, run_config)
        if not records:
            checks.append(CheckResult(baseline.name, False, "no applicable cases to verify"))
            continue
        mismatches = []
        for rec in records:
            ok, detail = match_expectation(rec, baseline.expect)
            if not ok:
                mismatches.append(f"{rec.case_id}: {detail}")
        if mismatches:
            checks.append(CheckResult(baseline.name, False, "; ".join(mismatches)))
        else:
            checks.append(CheckResult(baseline.name, True, f"{len(records)} case(s) matched expectation"))
    return GateResult("baselines", checks)
