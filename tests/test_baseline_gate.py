from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.pipeline import PipelineScore, Stage, StageResult  # noqa: E402
from core.record_schema import RowRecord  # noqa: E402
from baselines.base import Expectation  # noqa: E402
from gates.base import CheckResult, GateReport, GateResult, match_expectation  # noqa: E402


def _record(stages, capped_by):
    return RowRecord(
        case_id="c", task="t", model="m", provider="p",
        pipeline=PipelineScore(stages=stages, capped_by=capped_by),
        raw_output="", parsed_output=None, tokens_in=0, tokens_out=0,
        latency_ms=0.0, run_id="r",
    )


def test_match_should_pass_true_when_clean():
    rec = _record([StageResult(Stage.RETRIEVAL, 1.0, True)], None)
    ok, _ = match_expectation(rec, Expectation(should_pass=True))
    assert ok


def test_match_should_pass_fails_when_capped():
    rec = _record([StageResult(Stage.RETRIEVAL, 0.0, False, tags=["no_evidence_cited"])], "retrieval")
    ok, detail = match_expectation(rec, Expectation(should_pass=True))
    assert not ok and "retrieval" in detail


def test_match_fail_requires_a_failing_stage():
    rec = _record([StageResult(Stage.RETRIEVAL, 1.0, True)], None)
    ok, _ = match_expectation(rec, Expectation(should_pass=False))
    assert not ok  # expected FAIL but nothing failed


def test_match_fail_checks_capped_by_and_tags():
    rec = _record(
        [StageResult(Stage.RETRIEVAL, 0.3, False, tags=["cite_all_evidence"])], "retrieval"
    )
    ok, _ = match_expectation(
        rec, Expectation(should_pass=False, capped_by=Stage.RETRIEVAL, require_tags=("cite_all_evidence",))
    )
    assert ok
    ok2, detail2 = match_expectation(
        rec, Expectation(should_pass=False, capped_by=Stage.SAFETY)
    )
    assert not ok2 and "safety" in detail2


def test_gate_result_and_report_passed_properties():
    gr_ok = GateResult("g", [CheckResult("a", True, ""), CheckResult("b", True, "")])
    gr_bad = GateResult("g", [CheckResult("a", False, "")])
    assert gr_ok.passed and not gr_bad.passed
    assert GateReport([gr_ok]).passed
    assert not GateReport([gr_ok, gr_bad]).passed


# --- Task 5: baseline gate against the real scorer ---------------------------

import json  # noqa: E402
from core.dataset import load_cases  # noqa: E402
from core.runner import RunConfig  # noqa: E402
from baselines.base import Baseline  # noqa: E402
from plugins.agent_reasoning.plugin import AgentReasoningPlugin  # noqa: E402
from gates.baseline_gate import run_baseline_gate  # noqa: E402

TEACHING = "datasets/teaching/agent_reasoning/cases.json"


def _rc():
    return RunConfig(run_id="gate-test", model="baseline", provider="test")


def test_real_baselines_all_pass():
    plugin = AgentReasoningPlugin()
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    assert result.passed, [(c.name, c.detail) for c in result.checks if not c.passed]
    assert {c.name for c in result.checks} == {
        "empty_output", "schema_only", "no_op", "cite_all", "unsafe_sensitive", "oracle"
    }


def test_gate_has_teeth_catches_scorer_hole():
    # A baseline emitting oracle-CORRECT output but declaring should_pass=False
    # simulates a scorer hole: the gate must report MISMATCH.
    plugin = AgentReasoningPlugin()
    sneaky = Baseline("sneaky", lambda case: json.dumps(case["_oracle"]), Expectation(should_pass=False))
    plugin.baselines = lambda: [sneaky]  # type: ignore[method-assign]
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    assert not result.passed


def test_gate_skips_inapplicable_cases():
    # oracle only applies where _oracle exists; unsafe_sensitive only to sensitive.
    plugin = AgentReasoningPlugin()
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    unsafe = next(c for c in result.checks if c.name == "unsafe_sensitive")
    assert unsafe.passed  # ran on the 1 sensitive case, skipped the commute case

