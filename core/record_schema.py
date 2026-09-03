"""Row-level record schema.

One record per case/model pair. The record's source of truth is `pipeline`
(the stage-by-stage PipelineScore). `legacy_score` is a convenience rollup
for tools that still expect a single number (quick CLI printouts, simple
sort-by-score views) -- it is always derived, never authoritative, and
nothing in the scoring logic should ever branch on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.pipeline import PipelineScore


@dataclass
class RowRecord:
    case_id: str
    task: str
    model: str
    provider: str
    pipeline: PipelineScore

    raw_output: str
    parsed_output: dict[str, Any] | None

    tokens_in: int
    tokens_out: int
    latency_ms: float

    run_id: str
    seed: int | None = None
    resolved_config: dict[str, Any] = field(default_factory=dict)
    skip_reason: str | None = None

    @property
    def failure_tags(self) -> list[str]:
        return self.pipeline.all_tags()

    @property
    def legacy_score(self) -> float | None:
        """Derived single-number rollup, for backward compatibility only."""
        return self.pipeline.weighted_mean()

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "task": self.task,
            "model": self.model,
            "provider": self.provider,
            "stages": {
                s.stage.value: {
                    "score": s.score,
                    "passed": s.passed,
                    "weight": s.weight,
                    "tags": s.tags,
                    "details": s.details,
                }
                for s in self.pipeline.stages
            },
            "capped_by": self.pipeline.capped_by,
            "legacy_score": self.legacy_score,
            "failure_tags": self.failure_tags,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "latency_ms": self.latency_ms,
            "run_id": self.run_id,
            "seed": self.seed,
            "resolved_config": self.resolved_config,
            "skip_reason": self.skip_reason,
        }
