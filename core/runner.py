"""Shared execution core.

The runner never scores task logic itself. For each case it:
  1. calls the plugin's `generate`,
  2. times it and reads token usage back,
  3. asks the plugin to score its own task-specific stages,
  4. appends the runner-owned COST and LATENCY stages,
  5. writes one RowRecord per case/model pair.

Nothing about retrieval, reasoning, action selection, or safety lives here --
that stays in the plugin. Adding a new benchmark surface means writing a new
plugin, not touching this file.
"""

from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from core.cost import score_cost_stage
from core.latency import score_latency_stage
from core.pipeline import PipelineScore, StageResult
from core.record_schema import RowRecord
from plugins.base import TaskPlugin


@dataclass
class RunConfig:
    run_id: str
    model: str
    provider: str
    cost_budget_usd: float | None = None
    latency_budget_ms: float | None = None
    seed: int | None = None


def run_case(
    plugin: TaskPlugin,
    case: dict[str, Any],
    model_call: Callable[..., Any],
    config: RunConfig,
) -> RowRecord:
    plugin.validate_stages()

    start = time.perf_counter()
    result = plugin.generate(case, model_call)
    latency_ms = (time.perf_counter() - start) * 1000

    task_stages = plugin.score(case, result)
    _validate_stage_coverage(plugin, task_stages)

    cost_stage = score_cost_stage(
        result.tokens_in,
        result.tokens_out,
        model=config.model,
        budget_usd=config.cost_budget_usd,
    )
    latency_stage = score_latency_stage(latency_ms, budget_ms=config.latency_budget_ms)

    all_stages = [*task_stages, cost_stage, latency_stage]
    capped_by = next((s.stage.value for s in all_stages if not s.passed and s.weight > 0), None)

    pipeline = PipelineScore(stages=all_stages, capped_by=capped_by)

    return RowRecord(
        case_id=case["case_id"],
        task=plugin.name,
        model=config.model,
        provider=config.provider,
        pipeline=pipeline,
        raw_output=result.raw_output,
        parsed_output=result.parsed_output,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        latency_ms=latency_ms,
        run_id=config.run_id,
        seed=config.seed,
    )


def _validate_stage_coverage(plugin: TaskPlugin, stages: list[StageResult]) -> None:
    got = {s.stage for s in stages}
    expected = set(plugin.STAGES)
    if got != expected:
        missing = expected - got
        unexpected = got - expected
        raise ValueError(
            f"{plugin.name}.score() stage mismatch -- "
            f"missing={sorted(s.value for s in missing)} "
            f"unexpected={sorted(s.value for s in unexpected)}"
        )


def new_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def run_batch(
    plugin: TaskPlugin,
    cases: list[dict[str, Any]],
    model_calls: dict[str, Callable[[str], str]],
    run_configs: dict[str, RunConfig],
    concurrency: int = 1,
    on_result: Callable[[RowRecord], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> list[RowRecord]:
    """Run every (case, model) pair. A failure in one unit becomes a record
    with `skip_reason` set, so one bad case never aborts the whole run.
    Results are returned sorted by (case_id, model) for reproducibility.

    on_result, if given, is invoked on the main thread once per finished unit.
    should_cancel, if given, is polled between finished units; when it returns
    True, not-yet-started units are cancelled and partial results returned."""
    units = [(case, model) for case in cases for model in model_calls]

    def _one(unit: tuple[dict[str, Any], str]) -> RowRecord:
        case, model = unit
        try:
            return run_case(plugin, case, model_calls[model], run_configs[model])
        except Exception as e:  # noqa: BLE001 - isolate one case's failure
            rc = run_configs[model]
            return RowRecord(
                case_id=case.get("case_id", "<unknown>"),
                task=plugin.name,
                model=model,
                provider=rc.provider,
                pipeline=PipelineScore(stages=[]),
                raw_output="",
                parsed_output=None,
                tokens_in=0,
                tokens_out=0,
                latency_ms=0.0,
                run_id=rc.run_id,
                seed=rc.seed,
                skip_reason=f"{type(e).__name__}: {e}",
            )

    records: list[RowRecord] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = [pool.submit(_one, u) for u in units]
        for fut in as_completed(futures):
            if should_cancel is not None and should_cancel():
                for f in futures:
                    f.cancel()
                break
            rec = fut.result()
            if on_result is not None:
                on_result(rec)
            records.append(rec)

    records.sort(key=lambda r: (r.case_id, r.model))
    return records
