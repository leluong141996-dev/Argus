"""Shared constants and helpers for the `multimodal_matching` task.

No scoring logic lives here -- just the sentinel, the value-normalization
used for label comparison, and the machine-readable failure tags that the
scorer, the baselines, and the tests all reference by name.
"""

from __future__ import annotations

# The value expected.label / a parsed output's "label" take to mean
# "no candidate matches". Correct behaviour on an abstain case is to emit a
# label of ABSTAIN too.
ABSTAIN = None

# Failure/behaviour tags (single source of truth).
INVALID_JSON = "invalid_json"
HALLUCINATED_LABEL = "hallucinated_label"
WRONG_LABEL = "wrong_label"
SHOULD_ABSTAIN = "should_abstain"
MISSED_MATCH = "missed_match"
UNSAFE_MATCH = "unsafe_match"


def normalize(value: object) -> str:
    """Normalize a label for exact-match comparison: string-coerce, strip
    surrounding whitespace, lowercase. Trivial formatting differences
    ("Red_Fox " vs "red_fox") must not fail an otherwise-correct answer."""
    return str(value).strip().lower()
