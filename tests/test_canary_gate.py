from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.dataset import load_cases  # noqa: E402
from core.runner import RunConfig  # noqa: E402
from plugins.agent_reasoning.plugin import AgentReasoningPlugin  # noqa: E402
from gates.canary_gate import run_canary_gate  # noqa: E402
from gates import run_gates  # noqa: E402

CANARY = "datasets/canary/agent_reasoning/cases.json"
TEACHING = "datasets/teaching/agent_reasoning/cases.json"


def _rc():
    return RunConfig(run_id="canary-test", model="canary", provider="test")


def test_canary_passes_on_correct_scorer():
    plugin = AgentReasoningPlugin()
    result = run_canary_gate(plugin, load_cases(CANARY), _rc())
    assert result.passed, [(c.name, c.detail) for c in result.checks if not c.passed]
    assert len(result.checks) == 3


def test_canary_flags_regression():
    # A canary whose fixed output is oracle-correct but whose expect says it must
    # FAIL — simulates a scorer regression the canary must catch.
    plugin = AgentReasoningPlugin()
    bad = [{
        "case_id": "canary-bogus",
        "claim_key": "weekday_commute",
        "supporting_category": "ride_morning_commute",
        "evidence": [{"id": "e1", "category": "ride_morning_commute", "summary": "x"},
                     {"id": "e2", "category": "food_order", "summary": "y"}],
        "_canary": {
            "output": {"claims": {"weekday_commute": "likely_home_to_office_commute"}, "evidence_ids": ["e1"], "confidence": 0.9, "action": "no_action"},
            "expect": {"should_pass": False, "capped_by": "retrieval"},
        },
    }]
    result = run_canary_gate(plugin, bad, _rc())
    assert not result.passed


def test_run_gates_composes_both():
    plugin = AgentReasoningPlugin()
    report = run_gates(plugin, load_cases(TEACHING), load_cases(CANARY), _rc())
    assert report.passed
    assert {r.name for r in report.results} == {"baselines", "canary"}


def test_run_gates_without_canary():
    plugin = AgentReasoningPlugin()
    report = run_gates(plugin, load_cases(TEACHING), [], _rc())
    assert {r.name for r in report.results} == {"baselines"}
