"""Contract-specific shortcut baselines for `tool_use`.

The shared `generic_baselines()` in baselines/shared.py hard-codes the
agent_reasoning stage set (RETRIEVAL) and tag vocabulary in its
Expectations, so it does not apply here. tool_use declares its own full
set. Each shortcut returns None for cases where it does not apply (the gate
skips those); the Expectation says how the scorer must reject it, or -- for
oracle -- that it must pass.
"""

from __future__ import annotations

import json
from typing import Any

from baselines.base import Baseline, Expectation
from plugins.tool_use import ontology as O


def _empty_output(case: dict[str, Any]) -> str:
    return ""


def _schema_only(case: dict[str, Any]) -> str | None:
    # "{}" parses to no tool → abstain. Only a genuine shortcut (must fail)
    # on tool-required cases; skip abstain cases where it would rightly pass.
    if case["expected"]["tool"] is O.ABSTAIN:
        return None
    return "{}"


def _no_op(case: dict[str, Any]) -> str | None:
    if case["expected"]["tool"] is O.ABSTAIN:
        return None
    return json.dumps({"tool": None, "arguments": {}})


def _fixed_tool(case: dict[str, Any]) -> str | None:
    # Always pick the first-listed tool with empty args. A genuine shortcut
    # only where the first tool is not the expected one.
    first = case["tools"][0]["name"]
    if first == case["expected"]["tool"]:
        return None
    return json.dumps({"tool": first, "arguments": {}})


def _unsafe_tool(case: dict[str, Any]) -> str | None:
    expected = case["expected"]["tool"]
    destructive = [t["name"] for t in case["tools"]
                   if t.get("destructive") and t["name"] != expected]
    if not destructive:
        return None
    return json.dumps({"tool": destructive[0], "arguments": {}})


def _oracle(case: dict[str, Any]) -> str:
    return json.dumps(case["expected"])


def contract_baselines() -> list[Baseline]:
    return [
        Baseline("empty_output", _empty_output,
                 Expectation(should_pass=False, require_tags=(O.INVALID_JSON,))),
        Baseline("schema_only", _schema_only, Expectation(should_pass=False)),
        Baseline("no_op", _no_op, Expectation(should_pass=False)),
        Baseline("fixed_tool", _fixed_tool, Expectation(should_pass=False)),
        Baseline("unsafe_tool", _unsafe_tool,
                 Expectation(should_pass=False, require_tags=(O.UNSAFE_TOOL_CALL,))),
        Baseline("oracle", _oracle, Expectation(should_pass=True)),
    ]
