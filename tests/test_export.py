from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.pipeline import PipelineScore, Stage, StageResult  # noqa: E402
from core.record_schema import RowRecord  # noqa: E402
from core.report_io import read_records  # noqa: E402
from dashboards.export import export_report  # noqa: E402


def _rec(case_id="c1"):
    ps = PipelineScore(stages=[StageResult(Stage.RETRIEVAL, 1.0, True)], capped_by=None)
    return RowRecord(case_id=case_id, task="agent_reasoning", model="m", provider="mock",
                     pipeline=ps, raw_output="{}", parsed_output={}, tokens_in=0, tokens_out=0,
                     latency_ms=0, run_id="r1")


def test_export_report_writes_m1_shape(tmp_path):
    out = tmp_path / "report.json"
    export_report([_rec("c1"), _rec("c2")], str(out))
    rows = read_records(str(out))
    assert [r["case_id"] for r in rows] == ["c1", "c2"]
    assert "stages" in rows[0] and "retrieval" in rows[0]["stages"]
