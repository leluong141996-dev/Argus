"""Latency stage: computed by the runner from wall-clock timing, never by a
task plugin. Mirrors core/cost.py -- both COST and LATENCY are runner-owned
stages (see core.pipeline.RUNNER_OWNED_STAGES) so plugin authors only ever
implement task-specific stages.
"""

from __future__ import annotations

from core.pipeline import Stage, StageResult


def score_latency_stage(latency_ms: float, *, budget_ms: float | None = None) -> StageResult:
    """Informational by default (weight=0, always `passed`) unless a
    `budget_ms` ceiling is configured, in which case going over budget fails
    the stage and gives it weight so it can gate the row."""
    if budget_ms is None:
        return StageResult(
            stage=Stage.LATENCY,
            score=1.0,
            passed=True,
            weight=0.0,
            details={"latency_ms": round(latency_ms, 1), "budget_ms": None},
        )

    within_budget = latency_ms <= budget_ms
    if budget_ms > 0:
        score = max(0.0, 1.0 - (latency_ms / budget_ms))
    else:
        score = 1.0 if latency_ms == 0 else 0.0

    return StageResult(
        stage=Stage.LATENCY,
        score=round(score, 4),
        passed=within_budget,
        tags=[] if within_budget else ["over_latency_budget"],
        details={"latency_ms": round(latency_ms, 1), "budget_ms": budget_ms},
    )
