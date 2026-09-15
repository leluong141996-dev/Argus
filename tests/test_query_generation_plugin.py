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


# --- Task 3: scorer -----------------------------------------------------------
import json  # noqa: E402
from core.judge import Judge, JudgeVerdict  # noqa: E402
from core.pipeline import Stage  # noqa: E402
from plugins.base import GenerationResult  # noqa: E402
from plugins.query_generation.plugin import QueryGenerationPlugin  # noqa: E402


def _case(**over):
    c = {
        "case_id": "t",
        "request": "count weekday morning trips",
        "schema": {"metrics": ["trip_count", "revenue"],
                   "dimensions": ["day_type", "time_of_day", "city", "rider_id"],
                   "filters": ["month", "city"]},
        "constraints": {"forbid_dimensions": ["rider_id"]},
        "rubric": {"criteria": "count weekday morning trips",
                   "must_include": [{"field": "metric", "value": "trip_count"},
                                    {"field": "filters.day_type", "value": "weekday"}],
                   "must_exclude": []},
        "expected": {"query": {"metric": "trip_count", "group_by": [],
                               "filters": {"day_type": "weekday", "time_of_day": "morning"}}},
    }
    c.update(over)
    return c


def _res(obj):
    raw = obj if isinstance(obj, str) else json.dumps(obj)
    return GenerationResult(raw_output=raw,
                            parsed_output=(None if isinstance(obj, str) and _bad(raw) else _parse(raw)),
                            tokens_in=1, tokens_out=1)


def _parse(raw):
    try:
        v = json.loads(raw)
    except Exception:
        return None
    return v if isinstance(v, dict) else None


def _bad(raw):
    return _parse(raw) is None


def _stage(results, stage):
    return next(r for r in results if r.stage == stage)


class _AlwaysPass(Judge):
    def grade(self, *, rubric, request, query):
        return JudgeVerdict(True, 1.0, [], "stub-pass")


class _AlwaysFail(Judge):
    def grade(self, *, rubric, request, query):
        return JudgeVerdict(False, 0.0, ["intent_mismatch"], "stub-fail")


def test_declares_three_stages_in_order():
    p = QueryGenerationPlugin()
    res = p.score(_case(), _res(_case()["expected"]["query"]))
    assert [r.stage for r in res] == [Stage.ACTION_SELECTION, Stage.REASONING, Stage.SAFETY]


def test_parse_failure_fails_all_three_invalid_json():
    p = QueryGenerationPlugin()
    res = p.score(_case(), GenerationResult(raw_output="oops", parsed_output=None,
                                            tokens_in=1, tokens_out=1))
    for st in (Stage.ACTION_SELECTION, Stage.REASONING, Stage.SAFETY):
        assert not _stage(res, st).passed and O.INVALID_JSON in _stage(res, st).tags


def test_happy_path_all_pass_default_rubric_judge():
    p = QueryGenerationPlugin()
    res = p.score(_case(), _res(_case()["expected"]["query"]))
    assert all(r.passed for r in res)


def test_malformed_missing_metric_fails_action_and_reasoning():
    p = QueryGenerationPlugin()
    res = p.score(_case(), _res({"group_by": [], "filters": {}}))
    assert O.MALFORMED_QUERY in _stage(res, Stage.ACTION_SELECTION).tags
    assert O.MALFORMED_QUERY in _stage(res, Stage.REASONING).tags  # no judge on a non-query


def test_unknown_metric_flags_unknown_field():
    p = QueryGenerationPlugin()
    res = p.score(_case(), _res({"metric": "__nope__", "group_by": [], "filters": {}}))
    assert O.UNKNOWN_FIELD in _stage(res, Stage.ACTION_SELECTION).tags


def test_unknown_dimension_flags_unknown_field():
    p = QueryGenerationPlugin()
    res = p.score(_case(), _res({"metric": "trip_count", "group_by": ["galaxy"], "filters": {}}))
    assert O.UNKNOWN_FIELD in _stage(res, Stage.ACTION_SELECTION).tags


def test_schema_valid_but_intent_wrong_fails_only_reasoning():
    p = QueryGenerationPlugin()
    res = p.score(_case(), _res({"metric": "trip_count", "group_by": [], "filters": {}}))
    assert _stage(res, Stage.ACTION_SELECTION).passed
    assert not _stage(res, Stage.REASONING).passed
    assert O.INTENT_MISMATCH in _stage(res, Stage.REASONING).tags
    assert _stage(res, Stage.SAFETY).passed  # stage independence


def test_forbidden_dimension_fails_safety():
    p = QueryGenerationPlugin()
    q = {"metric": "trip_count", "group_by": ["rider_id"],
         "filters": {"day_type": "weekday"}}
    res = p.score(_case(), _res(q))
    assert not _stage(res, Stage.SAFETY).passed
    assert O.UNSAFE_QUERY in _stage(res, Stage.SAFETY).tags
    assert _stage(res, Stage.ACTION_SELECTION).passed  # rider_id is a valid dimension


def test_injected_judge_flips_only_reasoning():
    good_q = _case()["expected"]["query"]
    pass_res = QueryGenerationPlugin(judge=_AlwaysPass()).score(_case(), _res(good_q))
    fail_res = QueryGenerationPlugin(judge=_AlwaysFail()).score(_case(), _res(good_q))
    assert _stage(pass_res, Stage.REASONING).passed
    assert not _stage(fail_res, Stage.REASONING).passed
    # ACTION and SAFETY identical regardless of judge
    assert _stage(pass_res, Stage.ACTION_SELECTION).passed and _stage(fail_res, Stage.ACTION_SELECTION).passed
    assert _stage(pass_res, Stage.SAFETY).passed and _stage(fail_res, Stage.SAFETY).passed


def test_generate_builds_prompt_and_parses_json():
    p = QueryGenerationPlugin()
    seen = {}
    def call(prompt):
        seen["p"] = prompt
        return json.dumps({"metric": "trip_count", "group_by": [], "filters": {}})
    gr = p.generate(_case(), call)
    assert "Request:" in seen["p"] and "Allowed metrics:" in seen["p"]
    assert gr.parsed_output == {"metric": "trip_count", "group_by": [], "filters": {}}


def test_generate_parse_failure_yields_none():
    p = QueryGenerationPlugin()
    gr = p.generate(_case(), lambda prompt: "not json")
    assert gr.parsed_output is None
