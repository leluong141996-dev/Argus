"""Shared constants and helpers for the `tool_use` task.

No scoring logic lives here -- just the sentinel, the value-normalization
used for argument comparison, and the machine-readable failure tags that
the scorer, the baselines, and the tests all reference by name.
"""

from __future__ import annotations

# The value expected.tool / a parsed output's "tool" take to mean "call no
# tool". Correct behaviour on a case whose expected.tool is ABSTAIN is to
# emit a tool of ABSTAIN too.
ABSTAIN = None

# Failure/behaviour tags (single source of truth).
INVALID_JSON = "invalid_json"
HALLUCINATED_TOOL = "hallucinated_tool"
WRONG_TOOL = "wrong_tool"
SHOULD_ABSTAIN = "should_abstain"
MISSING_REQUIRED_PARAM = "missing_required_param"
UNKNOWN_PARAM = "unknown_param"
WRONG_PARAM_VALUE = "wrong_param_value"
UNSAFE_TOOL_CALL = "unsafe_tool_call"


def normalize(value: object) -> str:
    """Normalize a parameter value for lenient comparison: string-coerce,
    strip surrounding whitespace, lowercase. Trivial formatting differences
    ("Hanoi " vs "hanoi") must not fail an otherwise-correct answer."""
    return str(value).strip().lower()
