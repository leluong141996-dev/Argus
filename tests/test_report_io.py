from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.report_io import write_records, read_records  # noqa: E402
from core.runner import RunConfig, run_case  # noqa: E402
from plugins.agent_reasoning.plugin import AgentReasoningPlugin  # noqa: E402
from plugins.agent_reasoning.cases import COMMUTE_CASE  # noqa: E402


def test_write_then_read_roundtrips(tmp_path):
    rec = run_case(AgentReasoningPlugin(), COMMUTE_CASE,
                   lambda _p: "{}", RunConfig(run_id="r", model="m", provider="mock"))
    out = tmp_path / "sub" / "report.json"
    write_records([rec], str(out))
    data = read_records(str(out))
    assert isinstance(data, list) and len(data) == 1
    assert data[0]["case_id"] == COMMUTE_CASE["case_id"]
