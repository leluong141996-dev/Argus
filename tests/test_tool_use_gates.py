from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # noqa: E402

from baselines.base import Baseline, Expectation  # noqa: E402
from core.dataset import load_cases  # noqa: E402
from core.runner import RunConfig  # noqa: E402
from gates.baseline_gate import run_baseline_gate  # noqa: E402
from plugins.tool_use import ontology as O  # noqa: E402
from plugins.tool_use.plugin import ToolUsePlugin  # noqa: E402

TEACHING = "datasets/teaching/tool_use/cases.json"


def _rc():
    return RunConfig(run_id="gate-test", model="baseline", provider="test")


def test_real_baselines_all_pass():
    plugin = ToolUsePlugin()
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    assert result.passed, [(c.name, c.detail) for c in result.checks if not c.passed]
    assert {c.name for c in result.checks} == {
        "empty_output", "schema_only", "no_op", "fixed_tool", "unsafe_tool", "oracle"
    }


def test_gate_has_teeth_catches_scorer_hole():
    # A baseline emitting oracle-CORRECT output but declaring should_pass=False
    # simulates a scorer hole: the gate must report MISMATCH.
    plugin = ToolUsePlugin()
    sneaky = Baseline("sneaky", lambda case: json.dumps(case["expected"]), Expectation(should_pass=False))
    plugin.baselines = lambda: [sneaky]  # type: ignore[method-assign]
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    assert not result.passed


def test_unsafe_tool_flags_and_skips():
    # Run the gate; find the unsafe_tool check; assert it passed
    # (it ran on the destructive cases where a destructive tool != expected exists,
    # and was skipped on the rest). This confirms both require_tags=(UNSAFE_TOOL_CALL,)
    # enforcement and the None-skip behavior.
    plugin = ToolUsePlugin()
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    unsafe = next(c for c in result.checks if c.name == "unsafe_tool")
    assert unsafe.passed  # ran on applicable cases, skipped the rest
