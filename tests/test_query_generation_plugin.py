from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plugins.query_generation import ontology as O  # noqa: E402


def test_ontology_exposes_helpers_and_all_tags():
    assert O.normalize(" X ") == "x"
    assert O.get_path({"a": {"b": 1}}, "a.b") == 1
    assert O.get_path({}, "a") is O.MISSING
    tags = {O.INVALID_JSON, O.MALFORMED_QUERY, O.UNKNOWN_FIELD,
            O.UNSAFE_QUERY, O.INTENT_MISMATCH, O.JUDGE_ERROR}
    assert len(tags) == 6  # all distinct, all present
    assert O.INTENT_MISMATCH == "intent_mismatch"
    assert O.JUDGE_ERROR == "judge_error"
