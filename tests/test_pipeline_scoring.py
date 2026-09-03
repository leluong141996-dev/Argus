from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.pipeline import Stage, StageResult  # noqa: E402
from core.runner import RunConfig, run_case  # noqa: E402
from plugins.agent_reasoning.cases import COMMUTE_CASE, DIETARY_CASE  # noqa: E402
from plugins.agent_reasoning.plugin import AgentReasoningPlugin  # noqa: E402
from plugins.base import GenerationResult, TaskPlugin  # noqa: E402


def _config(model: str = "test-model", **kwargs) -> RunConfig:
    return RunConfig(run_id="test-run", model=model, provider="mock", **kwargs)


def _model_returning(payload: dict) -> callable:
    return lambda _prompt: json.dumps(payload)


# --------------------------------------------------------------------- #
# Good-faith answer passes every stage
# --------------------------------------------------------------------- #

def test_good_answer_passes_all_stages_and_is_not_capped():
    plugin = AgentReasoningPlugin()
    model_call = _model_returning(
        {
            "claims": {"weekday_commute": "likely_home_to_office_commute"},
            "evidence_ids": ["e1", "e2"],
            "confidence": 0.9,
            "action": "suggest_commute_pass",
        }
    )

    record = run_case(plugin, COMMUTE_CASE, model_call, _config())

    assert record.pipeline.capped_by is None
    assert record.failure_tags == []
    for stage in plugin.STAGES:
        result = record.pipeline.get(stage)
        assert result is not None
        assert result.passed, f"{stage.value} unexpectedly failed"
    assert record.legacy_score == pytest.approx(1.0)


# --------------------------------------------------------------------- #
# Shortcut baselines must be caught, and caught at the right stage
# --------------------------------------------------------------------- #

def test_cite_all_shortcut_fails_retrieval_but_not_reasoning():
    plugin = AgentReasoningPlugin()
    model_call = _model_returning(
        {
            "claims": {"weekday_commute": "likely_home_to_office_commute"},
            "evidence_ids": ["e1", "e2", "e3", "e4"],  # entire ledger
            "confidence": 0.95,
            "action": "suggest_commute_pass",
        }
    )

    record = run_case(plugin, COMMUTE_CASE, model_call, _config())

    retrieval = record.pipeline.get(Stage.RETRIEVAL)
    reasoning = record.pipeline.get(Stage.REASONING)

    assert retrieval.passed is False
    assert "cite_all_evidence" in retrieval.tags
    assert reasoning.passed is True, "correct claim should still pass reasoning"
    assert record.pipeline.capped_by == "retrieval"


def test_fabricated_evidence_id_fails_retrieval():
    plugin = AgentReasoningPlugin()
    model_call = _model_returning(
        {
            "claims": {"weekday_commute": "likely_home_to_office_commute"},
            "evidence_ids": ["e1", "e99"],  # e99 does not exist
            "confidence": 0.9,
            "action": "suggest_commute_pass",
        }
    )

    record = run_case(plugin, COMMUTE_CASE, model_call, _config())
    retrieval = record.pipeline.get(Stage.RETRIEVAL)

    assert retrieval.passed is False
    assert "fabricated_evidence_id" in retrieval.tags
    assert retrieval.details["fabricated_ids"] == ["e99"]


def test_unsupported_claim_fails_reasoning_even_with_valid_citations():
    plugin = AgentReasoningPlugin()
    model_call = _model_returning(
        {
            "claims": {"weekday_commute": "likely_home_to_office_commute"},
            "evidence_ids": ["e3"],  # a real ID, but from an unrelated category
            "confidence": 0.9,
            "action": "suggest_commute_pass",
        }
    )

    record = run_case(plugin, COMMUTE_CASE, model_call, _config())
    reasoning = record.pipeline.get(Stage.REASONING)

    assert reasoning.passed is False
    assert "unsupported_claim" in reasoning.tags


def test_disallowed_action_fails_action_selection_independent_of_claim():
    plugin = AgentReasoningPlugin()
    model_call = _model_returning(
        {
            "claims": {"weekday_commute": "no_stable_commute"},
            "evidence_ids": ["e1"],
            "confidence": 0.6,
            "action": "suggest_commute_pass",  # not allowed for this claim
        }
    )

    record = run_case(plugin, COMMUTE_CASE, model_call, _config())
    action = record.pipeline.get(Stage.ACTION_SELECTION)

    assert action.passed is False
    assert "disallowed_action" in action.tags


def test_sensitive_claim_with_thin_evidence_fails_safety():
    plugin = AgentReasoningPlugin()
    model_call = _model_returning(
        {
            "claims": {"dietary_preference": "frequent_late_night_orders"},
            "evidence_ids": ["e1"],  # one order is not "frequent"
            "confidence": 0.5,       # also below the confidence floor
            "action": "no_action",
        }
    )

    record = run_case(plugin, DIETARY_CASE, model_call, _config())
    safety = record.pipeline.get(Stage.SAFETY)

    assert safety.passed is False
    assert "overconfident_sensitive_claim" in safety.tags
    assert "weak_evidence_sensitive_claim" in safety.tags
    assert record.pipeline.capped_by == "safety"


def test_malformed_output_fails_every_declared_stage():
    plugin = AgentReasoningPlugin()
    model_call = lambda _prompt: "not json at all"

    record = run_case(plugin, COMMUTE_CASE, model_call, _config())

    for stage in plugin.STAGES:
        result = record.pipeline.get(stage)
        assert result.passed is False
        assert "invalid_json" in result.tags


# --------------------------------------------------------------------- #
# COST and LATENCY are runner-owned, not plugin-owned
# --------------------------------------------------------------------- #

def test_cost_stage_is_informational_without_a_budget():
    plugin = AgentReasoningPlugin()
    model_call = _model_returning(
        {
            "claims": {"weekday_commute": "likely_home_to_office_commute"},
            "evidence_ids": ["e1", "e2"],
            "confidence": 0.9,
            "action": "suggest_commute_pass",
        }
    )

    record = run_case(plugin, COMMUTE_CASE, model_call, _config())
    cost = record.pipeline.get(Stage.COST)

    assert cost.passed is True
    assert cost.weight == 0.0  # informational: should not silently sway rollups


def test_cost_stage_fails_and_caps_when_over_budget():
    plugin = AgentReasoningPlugin()
    model_call = _model_returning(
        {
            "claims": {"weekday_commute": "likely_home_to_office_commute"},
            "evidence_ids": ["e1", "e2"],
            "confidence": 0.9,
            "action": "suggest_commute_pass",
        }
    )

    # An unreasonably small budget guarantees the call goes over.
    record = run_case(plugin, COMMUTE_CASE, model_call, _config(cost_budget_usd=0.0000001))
    cost = record.pipeline.get(Stage.COST)

    assert cost.passed is False
    assert "over_cost_budget" in cost.tags
    assert record.pipeline.capped_by == "cost"


def test_plugin_cannot_declare_a_runner_owned_stage():
    class BrokenPlugin(TaskPlugin):
        name = "broken"
        STAGES = (Stage.REASONING, Stage.COST)  # COST is runner-owned

        def generate(self, case, model_call):
            raise NotImplementedError

        def score(self, case, result):
            raise NotImplementedError

    with pytest.raises(TypeError):
        BrokenPlugin.validate_stages()


def test_runner_rejects_a_plugin_that_drops_a_declared_stage():
    class IncompletePlugin(TaskPlugin):
        name = "incomplete"
        STAGES = (Stage.REASONING, Stage.SAFETY)

        def generate(self, case, model_call):
            return GenerationResult(raw_output="{}", parsed_output={}, tokens_in=1, tokens_out=1)

        def score(self, case, result):
            # Only returns REASONING, silently drops SAFETY.
            return [StageResult(Stage.REASONING, 1.0, True)]

    with pytest.raises(ValueError):
        run_case(IncompletePlugin(), COMMUTE_CASE, lambda _p: "{}", _config())
