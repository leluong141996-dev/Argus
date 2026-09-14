from __future__ import annotations
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.cli import main  # noqa: E402


MOCK_CONFIG = """
task: agent_reasoning
dataset: datasets/teaching/agent_reasoning/cases.json
models: [m-mock]
provider: {{name: mock}}
concurrency: 2
output: {out}
"""


def test_cli_run_end_to_end_writes_report(tmp_path):
    out = tmp_path / "report.json"
    cfg = tmp_path / "c.yaml"
    cfg.write_text(MOCK_CONFIG.format(out=str(out)))

    code = main(["run", "--config", str(cfg)])
    assert code == 0
    data = json.loads(out.read_text())
    assert len(data) >= 2  # two seeded cases
    assert all("stages" in row for row in data)


def test_cli_baselines_only_is_deferred(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(MOCK_CONFIG.format(out=str(tmp_path / "r.json")))
    code = main(["run", "--config", str(cfg), "--baselines-only"])
    assert code == 2  # planned for M2, not implemented


def test_cli_unknown_task_exits_nonzero(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("task: nope\ndataset: x\nmodels: [m]\nprovider: {name: mock}\n")
    code = main(["run", "--config", str(cfg)])
    assert code != 0
