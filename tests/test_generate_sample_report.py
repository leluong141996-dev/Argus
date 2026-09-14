from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.report_io import read_records  # noqa: E402
from examples.generate_sample_report import generate  # noqa: E402


def test_generate_writes_multi_row_report(tmp_path):
    out = tmp_path / "demo.json"
    generate(str(out))
    rows = read_records(str(out))
    assert len(rows) >= 2
    assert all(r.get("stages") for r in rows)
