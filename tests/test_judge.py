from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.judge import (  # noqa: E402
    JudgeVerdict, RubricJudge, LLMJudge, MISSING, get_path, normalize,
    INTENT_MISMATCH, JUDGE_ERROR,
)

RUBRIC = {
    "criteria": "count trips on weekday mornings",
    "must_include": [
        {"field": "metric", "value": "trip_count"},
        {"field": "filters.day_type", "value": "weekday"},
    ],
    "must_exclude": [],
}
GOOD = {"metric": "trip_count", "group_by": [], "filters": {"day_type": "weekday"}}


def test_get_path_reads_nested_and_reports_missing():
    assert get_path(GOOD, "filters.day_type") == "weekday"
    assert get_path(GOOD, "filters.nope") is MISSING
    assert get_path(GOOD, "metric.deep") is MISSING  # non-dict traversal


def test_normalize_coerces_strips_lowercases():
    assert normalize(" Weekday ") == "weekday"
    assert normalize(5) == "5"


def test_rubric_judge_passes_when_all_included():
    v = RubricJudge().grade(rubric=RUBRIC, request="r", query=GOOD)
    assert v.passed and v.score == 1.0 and v.tags == []


def test_rubric_judge_fails_intent_mismatch_when_criterion_unmet():
    bad = {"metric": "trip_count", "group_by": [], "filters": {}}
    v = RubricJudge().grade(rubric=RUBRIC, request="r", query=bad)
    assert not v.passed and INTENT_MISMATCH in v.tags
    assert v.score == 0.5  # 1 of 2 satisfied


def test_rubric_judge_fails_on_must_exclude():
    rubric = {"must_include": [], "must_exclude": [{"field": "metric", "value": "revenue"}]}
    q = {"metric": "revenue", "group_by": [], "filters": {}}
    v = RubricJudge().grade(rubric=rubric, request="r", query=q)
    assert not v.passed and v.score == 0.0 and INTENT_MISMATCH in v.tags


def test_rubric_judge_values_membership_and_list_actual():
    rubric = {"must_include": [{"field": "group_by", "values": ["city", "region"]}]}
    q = {"metric": "m", "group_by": ["City"], "filters": {}}
    assert RubricJudge().grade(rubric=rubric, request="r", query=q).passed


class _StubProvider:
    def __init__(self, reply):
        self._reply = reply
    def complete(self, prompt, *, model):
        return self._reply


def test_llm_judge_parses_valid_verdict():
    p = _StubProvider('{"passed": true, "score": 0.9, "rationale": "ok"}')
    v = LLMJudge(p, "judge-model").grade(rubric=RUBRIC, request="r", query=GOOD)
    assert v.passed and v.score == 0.9 and v.rationale == "ok" and v.tags == []


def test_llm_judge_fails_safe_on_junk():
    v = LLMJudge(_StubProvider("not json"), "m").grade(rubric=RUBRIC, request="r", query=GOOD)
    assert not v.passed and v.score == 0.0 and JUDGE_ERROR in v.tags


def test_llm_judge_fails_safe_on_out_of_range_score():
    p = _StubProvider('{"passed": true, "score": 1.7, "rationale": "x"}')
    v = LLMJudge(p, "m").grade(rubric=RUBRIC, request="r", query=GOOD)
    assert not v.passed and JUDGE_ERROR in v.tags


def test_llm_judge_fails_safe_on_provider_error():
    class _Boom:
        def complete(self, prompt, *, model):
            raise RuntimeError("gateway 502")
    v = LLMJudge(_Boom(), "m").grade(rubric=RUBRIC, request="r", query=GOOD)
    assert not v.passed and JUDGE_ERROR in v.tags
