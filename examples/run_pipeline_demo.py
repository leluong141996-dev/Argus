"""Runnable demo of pipeline-style scoring.

Runs the `agent_reasoning` plugin against two toy model behaviors -- a
well-behaved one and a shortcut one that cites the entire evidence ledger --
and prints a stage-by-stage report for each, plus a task/stage-level
summary. No network access or API key needed.

Run:
    python examples/run_pipeline_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.runner import RunConfig, run_case  # noqa: E402
from dashboards.aggregate import summarize  # noqa: E402
from plugins.agent_reasoning.cases import COMMUTE_CASE  # noqa: E402
from plugins.agent_reasoning.plugin import AgentReasoningPlugin  # noqa: E402


def good_agent(_prompt: str) -> str:
    """Cites only the evidence that actually supports the claim."""
    return json.dumps(
        {
            "claims": {"weekday_commute": "likely_home_to_office_commute"},
            "evidence_ids": ["e1", "e2"],
            "confidence": 0.9,
            "action": "suggest_commute_pass",
        }
    )


def cite_all_agent(_prompt: str) -> str:
    """Gets the claim right but cites the entire ledger indiscriminately --
    the exact shortcut RETRIEVAL is designed to catch."""
    return json.dumps(
        {
            "claims": {"weekday_commute": "likely_home_to_office_commute"},
            "evidence_ids": ["e1", "e2", "e3", "e4"],
            "confidence": 0.95,
            "action": "suggest_commute_pass",
        }
    )


def main() -> None:
    plugin = AgentReasoningPlugin()
    records = []

    for label, model_call in [("good-agent-v1", good_agent), ("cite-all-agent-v1", cite_all_agent)]:
        config = RunConfig(run_id="demo-run", model=label, provider="mock")
        record = run_case(plugin, COMMUTE_CASE, model_call, config)
        records.append(record)

        print(f"\n=== {label} on {record.case_id} ===")
        for stage_result in record.pipeline.stages:
            verdict = "PASS" if stage_result.passed else "FAIL"
            print(f"  [{verdict}] {stage_result.stage.value:<16} score={stage_result.score:.2f}  tags={stage_result.tags}")
        print(f"  capped_by={record.pipeline.capped_by}  legacy_score={record.legacy_score:.2f}")

    print("\n=== Task/stage-level summary (never one global score) ===")
    for summary in summarize(records):
        print(
            f"  {summary.task}/{summary.model:<18} {summary.stage:<16} "
            f"mean={summary.mean_score:.2f} pass_rate={summary.pass_rate:.2f} top_tags={summary.top_tags}"
        )


if __name__ == "__main__":
    main()
