from __future__ import annotations
import sys, json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.dataset import load_cases, DatasetError, split_of, require_split  # noqa: E402


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


def _write_cases(dirpath, cases):
    dirpath.mkdir(parents=True, exist_ok=True)
    p = dirpath / "cases.json"
    p.write_text(json.dumps({"cases": cases}))
    return str(p)


def test_load_cases_stamps_split_teaching(tmp_path):
    p = _write_cases(tmp_path / "datasets" / "teaching" / "t", [{"case_id": "a"}])
    cases = load_cases(p)
    assert all(c["_split"] == "teaching" for c in cases)


def test_load_cases_stamps_split_certification(tmp_path):
    p = _write_cases(tmp_path / "datasets" / "certification" / "t", [{"case_id": "a"}])
    cases = load_cases(p)
    assert all(c["_split"] == "certification" for c in cases)


def test_load_cases_split_none_outside_datasets(tmp_path):
    p = _write_cases(tmp_path / "scratch" / "t", [{"case_id": "a"}])
    cases = load_cases(p)
    assert all(c["_split"] is None for c in cases)


def test_require_split_passes_uniform():
    require_split([{"case_id": "a", "_split": "teaching"}], "teaching")  # no raise


def test_require_split_rejects_mixed():
    with pytest.raises(DatasetError):
        require_split(
            [{"case_id": "a", "_split": "teaching"},
             {"case_id": "b", "_split": "certification"}],
            "teaching",
        )


def test_require_split_rejects_unclassified():
    with pytest.raises(DatasetError):
        require_split([{"case_id": "a", "_split": None}], "teaching")


def test_certification_example_loads_and_classifies():
    cases = load_cases("datasets/certification/agent_reasoning/cases.example.json")
    assert cases
    assert all(c["_split"] == "certification" for c in cases)
