from __future__ import annotations
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core.cli as cli  # noqa: E402
import server.runs as runs_mod  # noqa: E402
from core.cli import main  # noqa: E402
from gates.base import CheckResult, GateReport, GateResult  # noqa: E402

MOCK_CONFIG = """
task: agent_reasoning
dataset: datasets/teaching/agent_reasoning/cases.json
models: [m-mock]
provider: {{name: mock}}
output: {out}
"""


def _cfg(tmp_path, out):
    p = tmp_path / "c.yaml"
    p.write_text(MOCK_CONFIG.format(out=str(out)))
    return p


def _failing_gates(*a, **k):
    return GateReport([GateResult("baselines", [CheckResult("empty_output", False, "shortcut passed!")])])


def test_gate_failure_blocks_run_and_writes_no_report(tmp_path, monkeypatch):
    monkeypatch.setattr(runs_mod, "run_gates", _failing_gates)
    out = tmp_path / "r.json"
    code = main(["run", "--config", str(_cfg(tmp_path, out))])
    assert code == 3
    assert not out.exists()  # no report on gate block


def test_no_gate_bypasses_preflight(tmp_path, monkeypatch):
    monkeypatch.setattr(runs_mod, "run_gates", _failing_gates)
    out = tmp_path / "r.json"
    code = main(["run", "--config", str(_cfg(tmp_path, out)), "--no-gate"])
    assert code == 0
    assert out.exists()  # real run proceeded despite the (bypassed) failing gate


def test_normal_run_passes_gate_then_writes_report(tmp_path):
    out = tmp_path / "r.json"
    code = main(["run", "--config", str(_cfg(tmp_path, out))])
    assert code == 0
    assert len(json.loads(out.read_text())) >= 2
