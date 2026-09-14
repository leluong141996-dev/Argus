from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.dataset import load_cases  # noqa: E402
from core.providers import as_model_call, build_provider  # noqa: E402
from core.registry import get_plugin  # noqa: E402
from core.runner import RunConfig, run_batch  # noqa: E402

_CASES = "datasets/teaching/agent_reasoning/cases.json"


def _fixtures():
    plugin = get_plugin("agent_reasoning")
    cases = load_cases(_CASES)
    provider = build_provider("mock", {})
    models = ("m1", "m2")
    model_calls = {m: as_model_call(provider, m) for m in models}
    run_configs = {m: RunConfig(run_id="t", model=m, provider="mock") for m in models}
    return plugin, cases, model_calls, run_configs


def test_on_result_called_once_per_unit_and_output_sorted():
    plugin, cases, mc, rc = _fixtures()
    seen = []
    out = run_batch(plugin, cases, mc, rc, concurrency=2, on_result=seen.append)
    assert len(seen) == len(cases) * len(mc)
    assert out == sorted(out, key=lambda r: (r.case_id, r.model))
    assert len(out) == len(seen)


def test_none_hooks_reproduce_default_behavior():
    plugin, cases, mc, rc = _fixtures()
    a = run_batch(plugin, cases, mc, rc, concurrency=1)
    b = run_batch(plugin, cases, mc, rc, concurrency=1, on_result=None, should_cancel=None)
    assert [(r.case_id, r.model) for r in a] == [(r.case_id, r.model) for r in b]


def test_should_cancel_stops_early():
    plugin, cases, mc, rc = _fixtures()
    total = len(cases) * len(mc)
    collected = []

    def cancel_after_one():
        return len(collected) >= 1

    out = run_batch(plugin, cases, mc, rc, concurrency=1,
                    on_result=collected.append, should_cancel=cancel_after_one)
    assert len(out) < total  # stopped before finishing all units
