"""Pipeline-style scoring primitives.

Instead of collapsing an agent's behavior into one opaque score, ARGUS scores
distinct stages of the pipeline separately: what it retrieved, how it
reasoned, what action it selected, how fast/expensive it was, and whether it
stayed safe. A task plugin declares which stages apply to it and scores each
one independently. Nothing here forces a single global number -- aggregation
stays task-level and stage-level, by design (see dashboards/aggregate.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Stage(str, Enum):
    """The fixed set of pipeline stages ARGUS knows how to score.

    A task plugin only implements the subset that applies to it -- e.g. a
    tool-calling task has no RETRIEVAL stage, and a pure code-diff task has
    no ACTION_SELECTION stage. COST and LATENCY are measured by the runner
    for every task automatically; plugins never compute them.
    """

    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    ACTION_SELECTION = "action_selection"
    SAFETY = "safety"
    COST = "cost"
    LATENCY = "latency"


# Stages the runner computes itself from run metadata, never from plugin logic.
RUNNER_OWNED_STAGES = frozenset({Stage.COST, Stage.LATENCY})


@dataclass
class StageResult:
    """The outcome of scoring a single pipeline stage.

    score:   normalized 0.0-1.0. For stages that are pass/fail by nature
             (e.g. SAFETY), use 1.0 / 0.0 and let `passed` carry the verdict.
    passed:  an explicit boolean verdict, independent of the numeric score,
             so a stage can be informational (score without a hard verdict)
             or gating (a fail here can cap the row -- see
             PipelineScore.capped_by).
    weight:  relative importance of this stage for task-level reporting.
             It never merges stages into one number inside the row record
             itself -- it only affects `PipelineScore.weighted_mean()`,
             which is an explicitly-derived rollup, not the row's ground
             truth.
    tags:    short machine-readable failure/behavior tags (e.g.
             "fabricated_evidence_id"), same vocabulary as flat failure
             tags used elsewhere in ARGUS.
    details: free-form, stage-specific evidence for debugging. Never used
             for scoring logic itself -- it exists for a human reading
             the row.
    """

    stage: Stage
    score: float
    passed: bool
    weight: float = 1.0
    tags: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"{self.stage.value} score must be in [0.0, 1.0], got {self.score}")
        if self.weight < 0:
            raise ValueError(f"{self.stage.value} weight must be >= 0, got {self.weight}")


@dataclass
class PipelineScore:
    """The full stage-by-stage scoring result for one case/model row.

    Deliberately has no single `.score` field. A row is "what happened at
    each stage", not a number. Any single-number rollup is a reporting-layer
    decision, computed on demand from these stages, never stored as the
    row's ground truth.
    """

    stages: list[StageResult]
    capped_by: str | None = None  # name of the gating stage that capped this row, if any

    def get(self, stage: Stage) -> StageResult | None:
        return next((s for s in self.stages if s.stage == stage), None)

    def stage_names(self) -> list[str]:
        return [s.stage.value for s in self.stages]

    def all_tags(self) -> list[str]:
        tags: list[str] = []
        for s in self.stages:
            tags.extend(s.tags)
        return tags

    def weighted_mean(self, *, exclude: frozenset[Stage] = frozenset()) -> float | None:
        """A convenience rollup for dashboards / quick printouts. Never used
        to gate a row -- gating is explicit via `capped_by` and each stage's
        `passed` flag."""
        relevant = [s for s in self.stages if s.stage not in exclude and s.weight > 0]
        if not relevant:
            return None
        total_weight = sum(s.weight for s in relevant)
        if total_weight == 0:
            return None
        return sum(s.score * s.weight for s in relevant) / total_weight
