"""Generate the dashboard's bundled demo report.

Runs the agent_reasoning plugin over its teaching cases through the offline
mock provider (no network), across two model labels, and writes an M1-shaped
report the dashboard can load. Deterministic run ids keep the bundled demo
stable across rebuilds.

Usage:
    python examples/generate_sample_report.py [out_path]
"""
from __future__ import annotations

import sys

from core.dataset import load_cases
from core.providers import as_model_call, build_provider
from core.runner import RunConfig, run_batch
from core.registry import get_plugin
from dashboards.export import export_report

_TASK = "agent_reasoning"
_CASES = f"datasets/teaching/{_TASK}/cases.json"
_MODELS = ("mock-fast", "mock-strong")
_DEFAULT_OUT = "dashboards/web/demo_report.json"


def generate(path: str = _DEFAULT_OUT) -> None:
    plugin = get_plugin(_TASK)
    cases = load_cases(_CASES)
    provider = build_provider("mock", {})
    model_calls = {m: as_model_call(provider, m) for m in _MODELS}
    run_configs = {
        m: RunConfig(run_id=f"demo-{m}", model=m, provider="mock", seed=0)
        for m in _MODELS
    }
    records = run_batch(plugin, cases, model_calls, run_configs, concurrency=1)
    export_report(records, path)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    out = argv[0] if argv else _DEFAULT_OUT
    generate(out)
    print(f"wrote demo report -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
