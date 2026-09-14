from __future__ import annotations
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.runner import run_batch, RunConfig  # noqa: E402
from plugins.agent_reasoning.plugin import AgentReasoningPlugin  # noqa: E402
from plugins.agent_reasoning.cases import COMMUTE_CASE, DIETARY_CASE  # noqa: E402

GOOD = json.dumps({
    "claims": {"weekday_commute": "likely_home_to_office_commute"},
    "evidence_ids": ["e1", "e2"], "confidence": 0.9, "action": "suggest_commute_pass",
})


def _rc(model):
    return RunConfig(run_id="r", model=model, provider="mock")


def test_run_batch_produces_one_record_per_case_model_in_stable_order():
    plugin = AgentReasoningPlugin()
    cases = [COMMUTE_CASE, DIETARY_CASE]
    calls = {"m1": lambda _p: GOOD}
    records = run_batch(plugin, cases, calls, {"m1": _rc("m1")}, concurrency=2)
    assert len(records) == 2
    # stable order: sorted by (case_id, model)
    assert [r.case_id for r in records] == sorted(c["case_id"] for c in cases)


def test_run_batch_captures_per_case_failure_as_skip_reason():
    plugin = AgentReasoningPlugin()

    def boom(_p):
        raise RuntimeError("provider exploded")

    records = run_batch(plugin, [COMMUTE_CASE], {"m1": boom}, {"m1": _rc("m1")}, concurrency=1)
    assert len(records) == 1
    assert records[0].skip_reason is not None
    assert "provider exploded" in records[0].skip_reason
