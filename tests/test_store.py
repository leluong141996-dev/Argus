from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.store import RunStore, RunMeta  # noqa: E402


def _store(tmp_path):
    s = RunStore(str(tmp_path / "t.db"))
    s.init_schema()
    return s


def test_insert_running_then_list_and_get(tmp_path):
    s = _store(tmp_path)
    s.insert_running(RunMeta(run_id="r1", task="agent_reasoning",
                             models=["m1", "m2"], provider="mock",
                             config="agent_reasoning.yaml", created_at="2026-09-14T00:00:00Z"))
    rows = s.list_runs()
    assert len(rows) == 1 and rows[0]["run_id"] == "r1"
    assert rows[0]["status"] == "running"
    assert rows[0]["models"] == ["m1", "m2"]
    got = s.get_run("r1")
    assert got["provider"] == "mock"


def test_finish_updates_status_and_counts(tmp_path):
    s = _store(tmp_path)
    s.insert_running(RunMeta(run_id="r1", task="t", models=["m"], provider="mock",
                             config="c.yaml", created_at="2026-09-14T00:00:00Z"))
    s.finish("r1", status="done", total=4, passed=3, failed=1,
             report_path="runs/r1/report.json")
    got = s.get_run("r1")
    assert got["status"] == "done"
    assert (got["total"], got["passed"], got["failed"]) == (4, 3, 1)
    assert got["report_path"] == "runs/r1/report.json"
    assert got["finished_at"] is not None


def test_get_unknown_returns_none(tmp_path):
    s = _store(tmp_path)
    assert s.get_run("nope") is None
