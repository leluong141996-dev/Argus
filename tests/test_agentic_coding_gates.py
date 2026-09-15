from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baselines.base import Baseline, Expectation  # noqa: E402
from core.dataset import load_cases  # noqa: E402
from core.runner import RunConfig  # noqa: E402
from gates.baseline_gate import run_baseline_gate  # noqa: E402
from plugins.agentic_coding.plugin import AgenticCodingPlugin  # noqa: E402

TEACHING = "datasets/teaching/agentic_coding/cases.json"


def _rc():
    return RunConfig(run_id="gate-test", model="baseline", provider="test")


def test_real_baselines_all_pass():
    plugin = AgenticCodingPlugin()  # default LocalSandbox -> deterministic
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    assert result.passed, [(c.name, c.detail) for c in result.checks if not c.passed]
    assert {c.name for c in result.checks} == {
        "empty_output", "no_change", "tamper_tests", "overfit_visible", "oracle"
    }


def test_overfit_visible_is_the_hidden_stage_teeth():
    # overfit_visible passes the visible suite but violates the hidden
    # invariant -- only the SAFETY (hidden) stage can catch it. Its gate check
    # must pass, proving the hidden-test stage is a real gate.
    plugin = AgenticCodingPlugin()
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    ov = next(c for c in result.checks if c.name == "overfit_visible")
    assert ov.passed


def test_overfit_visible_per_stage_visible_pass_hidden_fail():
    # Regression guard: the ac-idempotent-001 overfit patch must pass the
    # visible suite and be caught ONLY by the hidden (SAFETY) stage. If a
    # future edit makes it also fail visible, the gate-level teeth test would
    # still pass but the anti-gaming guarantee would be hollow -- this asserts
    # the real per-stage shape.
    from core.pipeline import Stage
    from plugins.base import GenerationResult
    case = next(c for c in load_cases(TEACHING) if c["case_id"] == "ac-idempotent-001")
    files = case["baselines"]["overfit_visible"]
    result = GenerationResult(raw_output=json.dumps({"files": files}),
                              parsed_output={"files": files}, tokens_in=1, tokens_out=1)
    stages = {r.stage: r for r in AgenticCodingPlugin().score(case, result)}
    assert stages[Stage.ACTION_SELECTION].passed
    assert stages[Stage.REASONING].passed          # visible tests genuinely pass
    assert not stages[Stage.SAFETY].passed         # only the hidden stage catches it


def test_gate_has_teeth_catches_scorer_hole():
    # An oracle-correct output declared should_pass=False simulates a scorer
    # hole: the gate must report a mismatch (not vacuously pass).
    plugin = AgenticCodingPlugin()
    sneaky = Baseline("sneaky",
                      lambda case: json.dumps({"files": case["expected"]["files"]}),
                      Expectation(should_pass=False))
    plugin.baselines = lambda: [sneaky]  # type: ignore[method-assign]
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    assert not result.passed
