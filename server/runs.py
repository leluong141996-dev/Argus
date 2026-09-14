"""Shared run orchestration: gate pre-flight -> run_batch -> return records.

Used by both the CLI (core.cli._run) and the server. Hooks let the server
stream progress and cancel; the CLI passes none. No FastAPI import."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from core.config import ArgusConfig
from core.dataset import load_cases
from core.providers import as_model_call, build_provider
from core.registry import get_plugin
from core.record_schema import RowRecord
from core.runner import run_batch
from gates import GateReport, run_gates


def _load_canary(task: str) -> list:
    path = f"datasets/canary/{task}/cases.json"
    if not os.path.exists(path):
        return []
    return load_cases(path)


class GateAborted(Exception):
    def __init__(self, report: GateReport):
        super().__init__("trust gate failed")
        self.report = report


@dataclass
class RunHooks:
    on_gate: Callable[[GateReport], None] | None = None
    on_start: Callable[[int], None] | None = None
    on_result: Callable[[RowRecord], None] | None = None
    on_done: Callable[[list[RowRecord]], None] | None = None
    on_error: Callable[[Exception], None] | None = None
    should_cancel: Callable[[], bool] | None = None


def execute_run(cfg: ArgusConfig, *, run_gate: bool,
                hooks: RunHooks | None = None) -> list[RowRecord]:
    hooks = hooks or RunHooks()
    plugin = get_plugin(cfg.task)
    cases = load_cases(cfg.dataset)

    if run_gate:
        canary = _load_canary(cfg.task)
        report = run_gates(plugin, cases, canary, cfg.run_config_for("baseline"))
        if hooks.on_gate:
            hooks.on_gate(report)
        if not report.passed:
            raise GateAborted(report)

    provider = build_provider(cfg.provider.name, cfg.provider.params)
    model_calls = {m: as_model_call(provider, m) for m in cfg.models}
    run_configs = {m: cfg.run_config_for(m) for m in cfg.models}

    if hooks.on_start:
        hooks.on_start(len(cases) * len(model_calls))

    records = run_batch(plugin, cases, model_calls, run_configs, cfg.concurrency,
                        on_result=hooks.on_result, should_cancel=hooks.should_cancel)
    if hooks.on_done:
        hooks.on_done(records)
    return records
