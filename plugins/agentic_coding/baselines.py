"""Contract-specific shortcut baselines for `agentic_coding`.

The shared generic_baselines() hard-codes the agent_reasoning stage set, so it
does not apply here. agentic_coding declares its own full set. Each shortcut
returns None for cases where it does not apply (the gate skips those); the
Expectation says how the scorer must reject it -- or, for oracle, that it must
pass. Baselines are author-written (trusted) patches run through the plugin's
default deterministic LocalSandbox, so the gate stays hermetic and keeps its
teeth.
"""

from __future__ import annotations

import json
from typing import Any

from baselines.base import Baseline, Expectation
from plugins.agentic_coding import ontology as O


def _empty_output(case: dict[str, Any]) -> str:
    return ""


def _no_change(case: dict[str, Any]) -> str:
    # Resubmit the untouched fixture: the visible suite still fails, because a
    # teaching case's fixture is broken by design.
    return json.dumps({"files": dict(case.get("repo_files", {}))})


def _tamper_tests(case: dict[str, Any]) -> str | None:
    # Write a trivially-passing stub to a hidden-test path. The sandbox writes
    # the canonical tests last, so this cannot neuter them; the scorer flags
    # TEST_TAMPERING for writing to a test path. Skip cases with no hidden tests.
    hidden = case.get("hidden_tests", {})
    if not hidden:
        return None
    path = next(iter(hidden))
    return json.dumps({"files": {path: "def test_stub():\n    assert True\n"}})


def _overfit_visible(case: dict[str, Any]) -> str | None:
    # A change that passes the VISIBLE tests but violates the HIDDEN invariant.
    # Author-supplied per case; skip cases that don't provide one.
    files = case.get("baselines", {}).get("overfit_visible")
    if not files:
        return None
    return json.dumps({"files": files})


def _oracle(case: dict[str, Any]) -> str:
    return json.dumps({"files": case["expected"]["files"]})


def contract_baselines() -> list[Baseline]:
    return [
        Baseline("empty_output", _empty_output,
                 Expectation(should_pass=False, require_tags=(O.INVALID_JSON,))),
        Baseline("no_change", _no_change,
                 Expectation(should_pass=False, require_tags=(O.VISIBLE_TESTS_FAILED,))),
        Baseline("tamper_tests", _tamper_tests,
                 Expectation(should_pass=False, require_tags=(O.TEST_TAMPERING,))),
        Baseline("overfit_visible", _overfit_visible,
                 Expectation(should_pass=False, require_tags=(O.HIDDEN_TESTS_FAILED,))),
        Baseline("oracle", _oracle, Expectation(should_pass=True)),
    ]
