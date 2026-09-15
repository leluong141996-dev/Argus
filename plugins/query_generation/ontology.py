"""Shared constants and helpers for the `query_generation` task.

Generic path/normalize helpers and the judge-owned tags come from core.judge
(the plugin depends on core, never the reverse); the query-generation-specific
failure tags are defined here. Single source of truth for every tag string the
scorer, the baselines, and the tests reference by name.
"""
from __future__ import annotations

from core.judge import (  # noqa: F401 - re-exported for a single import site
    MISSING, get_path, normalize, INTENT_MISMATCH, JUDGE_ERROR,
)

# Plugin-specific failure tags.
INVALID_JSON = "invalid_json"        # output was not a JSON object
MALFORMED_QUERY = "malformed_query"  # missing metric, or wrong-typed group_by/filters
UNKNOWN_FIELD = "unknown_field"      # metric/dimension/filter not in the case schema
UNSAFE_QUERY = "unsafe_query"        # used a constraints.forbid_dimensions field
# INTENT_MISMATCH, JUDGE_ERROR are re-exported from core.judge above.

__all__ = [
    "MISSING", "get_path", "normalize",
    "INVALID_JSON", "MALFORMED_QUERY", "UNKNOWN_FIELD", "UNSAFE_QUERY",
    "INTENT_MISMATCH", "JUDGE_ERROR",
]
