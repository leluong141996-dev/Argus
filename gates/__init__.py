"""Trust gates: run baselines/canaries through the real scorer and block an
untrustworthy run."""
from __future__ import annotations

from typing import Any

from core.runner import RunConfig
from gates.base import CheckResult, GateReport, GateResult
from gates.baseline_gate import run_baseline_gate
from gates.canary_gate import run_canary_gate
from plugins.base import TaskPlugin

__all__ = ["run_gates", "GateReport", "GateResult", "CheckResult"]


def run_gates(
    plugin: TaskPlugin,
    cases: list[dict[str, Any]],
    canary_cases: list[dict[str, Any]],
    run_config: RunConfig,
) -> GateReport:
    results = [run_baseline_gate(plugin, cases, run_config)]
    if canary_cases:
        results.append(run_canary_gate(plugin, canary_cases, run_config))
    return GateReport(results)
