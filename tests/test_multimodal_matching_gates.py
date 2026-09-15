from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json  # noqa: E402
from core.dataset import load_cases  # noqa: E402
from core.runner import RunConfig  # noqa: E402
from baselines.base import Baseline, Expectation  # noqa: E402
from gates.baseline_gate import run_baseline_gate  # noqa: E402
from plugins.multimodal_matching.plugin import MultimodalMatchingPlugin  # noqa: E402
from plugins.multimodal_matching import ontology as O  # noqa: E402

TEACHING = "datasets/teaching/multimodal_matching/cases.json"


def _rc():
    return RunConfig(run_id="gate-test", model="baseline", provider="test")


def test_real_baselines_all_pass():
    plugin = MultimodalMatchingPlugin()
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    assert result.passed, [(c.name, c.detail) for c in result.checks if not c.passed]
    assert {c.name for c in result.checks} == {
        "empty_output", "always_abstain", "first_label", "sensitive_label", "oracle"
    }


def test_gate_has_teeth_catches_scorer_hole():
    plugin = MultimodalMatchingPlugin()
    sneaky = Baseline("sneaky", lambda case: json.dumps(case["expected"]),
                      Expectation(should_pass=False))
    plugin.baselines = lambda: [sneaky]  # type: ignore[method-assign]
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    assert not result.passed


def test_sensitive_label_baseline_flags_and_skips():
    plugin = MultimodalMatchingPlugin()
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    check = next(c for c in result.checks if c.name == "sensitive_label")
    assert check.passed  # ran on the sensitive case(s), skipped the rest
