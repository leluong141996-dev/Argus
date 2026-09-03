"""Aggregate row records into task-level, stage-level summaries.

Deliberately produces one summary per (task, model, stage) triple -- never a
single global number across tasks or across stages. A setting that helps one
stage of one task can hurt another; collapsing everything into one ranking
throws that signal away.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from core.record_schema import RowRecord


@dataclass
class StageSummary:
    task: str
    model: str
    stage: str
    n: int
    mean_score: float
    pass_rate: float
    top_tags: list[tuple[str, int]]


def summarize(records: list[RowRecord], *, top_n_tags: int = 5) -> list[StageSummary]:
    buckets: dict[tuple[str, str, str], list] = defaultdict(list)
    for record in records:
        for stage_result in record.pipeline.stages:
            buckets[(record.task, record.model, stage_result.stage.value)].append(stage_result)

    summaries: list[StageSummary] = []
    for (task, model, stage), stage_results in buckets.items():
        n = len(stage_results)
        mean_score = sum(s.score for s in stage_results) / n
        pass_rate = sum(1 for s in stage_results if s.passed) / n

        tag_counts: dict[str, int] = defaultdict(int)
        for s in stage_results:
            for tag in s.tags:
                tag_counts[tag] += 1
        top_tags = sorted(tag_counts.items(), key=lambda kv: -kv[1])[:top_n_tags]

        summaries.append(
            StageSummary(
                task=task,
                model=model,
                stage=stage,
                n=n,
                mean_score=round(mean_score, 4),
                pass_rate=round(pass_rate, 4),
                top_tags=top_tags,
            )
        )

    summaries.sort(key=lambda s: (s.task, s.model, s.stage))
    return summaries
