from __future__ import annotations
import sys, json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.dataset import load_cases, DatasetError  # noqa: E402


def test_loads_seeded_agent_reasoning_cases():
    cases = load_cases("datasets/teaching/agent_reasoning/cases.json")
    assert len(cases) >= 2
    assert all("case_id" in c for c in cases)


def test_missing_file_raises_dataset_error():
    with pytest.raises(DatasetError):
        load_cases("nope/does_not_exist.json")


def test_case_without_case_id_raises(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"cases": [{"no_id": 1}]}))
    with pytest.raises(DatasetError):
        load_cases(str(p))
