from __future__ import annotations
import sys, json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.dataset import load_cases, DatasetError, split_of  # noqa: E402


def test_split_of_classifies_known_roots():
    assert split_of("datasets/teaching/agent_reasoning/cases.json") == "teaching"
    assert split_of("datasets/canary/agent_reasoning/cases.json") == "canary"
    assert split_of("datasets/certification/agent_reasoning/cases.json") == "certification"


def test_split_of_normalizes_and_handles_prefix():
    assert split_of("datasets/../datasets/teaching/x/cases.json") == "teaching"
    assert split_of("/home/u/Argus/datasets/teaching/x/cases.json") == "teaching"
    assert split_of("./datasets/canary/x/cases.json") == "canary"


def test_split_of_returns_none_for_unknown():
    assert split_of("nope/x.json") is None
    assert split_of("datasets/unknown/x/cases.json") is None
    assert split_of("datasets/cases.json") is None  # no split segment after datasets


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
