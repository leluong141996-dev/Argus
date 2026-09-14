from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import load_config  # noqa: E402
from server.runs import execute_run, RunHooks, GateAborted  # noqa: E402


def _mock_config(tmp_path):
    src = Path("configs/agent_reasoning.yaml").read_text().replace("name: groq", "name: mock")
    p = tmp_path / "mock.yaml"
    p.write_text(src)
    return load_config(str(p))


def test_execute_run_mock_returns_records_and_fires_hooks(tmp_path):
    cfg = _mock_config(tmp_path)
    seen, starts, dones = [], [], []
    hooks = RunHooks(on_result=seen.append, on_start=starts.append,
                     on_done=dones.append)
    records = execute_run(cfg, run_gate=True, hooks=hooks)
    assert len(records) >= 2
    assert len(seen) == len(records)
    assert starts and starts[0] == len(records)
    assert dones and dones[0] == records


def test_execute_run_no_hooks_still_runs(tmp_path):
    cfg = _mock_config(tmp_path)
    records = execute_run(cfg, run_gate=False)
    assert len(records) >= 2
