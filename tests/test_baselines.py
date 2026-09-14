from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from core.pipeline import Stage  # noqa: E402
from baselines.base import Baseline, Expectation  # noqa: E402


def test_expectation_defaults():
    e = Expectation(should_pass=False)
    assert e.should_pass is False
    assert e.capped_by is None
    assert e.require_tags == ()


def test_baseline_is_frozen_and_callable():
    b = Baseline("empty", lambda case: "", Expectation(False, Stage.RETRIEVAL, ("invalid_json",)))
    assert b.name == "empty"
    assert b.build_output({"case_id": "x"}) == ""
    assert b.expect.capped_by is Stage.RETRIEVAL
    with pytest.raises(Exception):
        b.name = "other"  # frozen


def test_generic_baselines_shape():
    from baselines.shared import generic_baselines
    names = [b.name for b in generic_baselines()]
    assert names == ["empty_output", "schema_only", "no_op"]


def test_generic_build_outputs():
    import json
    from baselines.shared import generic_baselines
    by_name = {b.name: b for b in generic_baselines()}
    case = {"case_id": "x", "claim_key": "weekday_commute", "evidence": []}
    assert by_name["empty_output"].build_output(case) == ""
    assert by_name["schema_only"].build_output(case) == "{}"
    parsed = json.loads(by_name["no_op"].build_output(case))
    assert parsed == {"claims": {}, "evidence_ids": [], "confidence": 0.0, "action": "no_action"}


def test_generic_expectations():
    from baselines.shared import generic_baselines
    by_name = {b.name: b for b in generic_baselines()}
    assert by_name["empty_output"].expect.should_pass is False
    assert by_name["empty_output"].expect.require_tags == ("invalid_json",)
    assert by_name["no_op"].expect.should_pass is False


def test_contract_baselines_shape():
    from plugins.agent_reasoning.baselines import contract_baselines
    names = [b.name for b in contract_baselines()]
    assert names == ["cite_all", "unsafe_sensitive", "oracle"]


def test_plugin_baselines_default_empty():
    from plugins.base import TaskPlugin

    class _Dummy(TaskPlugin):
        name = "dummy"

        def generate(self, case, model_call):
            return None

        def score(self, case, result):
            return []

    assert _Dummy().baselines() == []


def test_agent_reasoning_baselines_full_set():
    from plugins.agent_reasoning.plugin import AgentReasoningPlugin
    names = [b.name for b in AgentReasoningPlugin().baselines()]
    assert names == ["empty_output", "schema_only", "no_op", "cite_all", "unsafe_sensitive", "oracle"]


def test_cite_all_cites_every_id():
    import json
    from plugins.agent_reasoning.baselines import contract_baselines
    cite_all = {b.name: b for b in contract_baselines()}["cite_all"]
    case = {
        "claim_key": "weekday_commute",
        "evidence": [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}],
    }
    out = json.loads(cite_all.build_output(case))
    assert out["evidence_ids"] == ["e1", "e2", "e3"]
    assert out["claims"]["weekday_commute"] == "likely_home_to_office_commute"


def test_unsafe_sensitive_skips_nonsensitive_case():
    from plugins.agent_reasoning.baselines import contract_baselines
    unsafe = {b.name: b for b in contract_baselines()}["unsafe_sensitive"]
    nonsensitive = {"claim_key": "weekday_commute", "supporting_category": "ride_morning_commute", "evidence": []}
    assert unsafe.build_output(nonsensitive) is None


def test_oracle_returns_none_without_block():
    from plugins.agent_reasoning.baselines import contract_baselines
    oracle = {b.name: b for b in contract_baselines()}["oracle"]
    assert oracle.build_output({"case_id": "x"}) is None
