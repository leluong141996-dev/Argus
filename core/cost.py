"""Cost stage: computed by the runner from token usage, never by a task plugin.

Every provider call ARGUS makes returns token counts. Turning those into a
cost score is a runner-owned concern (Stage.COST is in RUNNER_OWNED_STAGES),
so a task plugin author never has to think about pricing tables.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.pipeline import Stage, StageResult


@dataclass(frozen=True)
class TokenPricing:
    """USD per 1,000 tokens."""

    input_per_1k: float
    output_per_1k: float


# Small built-in table so the demo runs with no external config. Real
# deployments should load this from a config file instead of hardcoding it.
DEFAULT_PRICING: dict[str, TokenPricing] = {
    "default": TokenPricing(input_per_1k=0.003, output_per_1k=0.015),
}


def compute_cost_usd(
    tokens_in: int,
    tokens_out: int,
    *,
    model: str = "default",
    pricing: dict[str, TokenPricing] | None = None,
) -> float:
    table = pricing or DEFAULT_PRICING
    rate = table.get(model, table["default"])
    return (tokens_in / 1000) * rate.input_per_1k + (tokens_out / 1000) * rate.output_per_1k


def score_cost_stage(
    tokens_in: int,
    tokens_out: int,
    *,
    model: str = "default",
    budget_usd: float | None = None,
    pricing: dict[str, TokenPricing] | None = None,
) -> StageResult:
    """Cost is informational by default (weight=0, always `passed`) unless a
    `budget_usd` ceiling is configured, in which case going over budget fails
    the stage and gives it weight so it can gate the row."""
    cost = compute_cost_usd(tokens_in, tokens_out, model=model, pricing=pricing)

    if budget_usd is None:
        return StageResult(
            stage=Stage.COST,
            score=1.0,
            passed=True,
            weight=0.0,
            details={"cost_usd": round(cost, 6), "budget_usd": None},
        )

    within_budget = cost <= budget_usd
    if budget_usd > 0:
        score = max(0.0, 1.0 - (cost / budget_usd))
    else:
        score = 1.0 if cost == 0 else 0.0

    return StageResult(
        stage=Stage.COST,
        score=round(score, 4),
        passed=within_budget,
        tags=[] if within_budget else ["over_cost_budget"],
        details={"cost_usd": round(cost, 6), "budget_usd": budget_usd},
    )
