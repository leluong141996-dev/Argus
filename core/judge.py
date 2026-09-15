"""LLM-judge infrastructure for open-ended task scoring.

Some task plugins (e.g. query_generation) grade an inherently open-ended
property -- does this output capture the requested intent? -- that has no
exact-match answer. That is scored by a Judge.

Two judge implementations, one contract:

  RubricJudge -- deterministic. Grades a candidate against explicit,
                 machine-checkable criteria carried in the case rubric.
                 Offline, hermetic, repeatable: the DEFAULT, and what the
                 baseline gate and the test suite run so shortcuts are caught
                 reliably.
  LLMJudge    -- a second model call, for real evaluations. Non-deterministic
                 by nature; injected only for live runs, never exercised by
                 gates/tests. Fails safe: any provider failure or an
                 unparseable / out-of-range verdict becomes a FAIL tagged
                 JUDGE_ERROR, never a silent pass.

Import direction: this module imports only from core.providers; it never
imports plugins/. Plugins depend on core, not the reverse.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from core.providers import Provider

# Judge-owned failure tags (single source of truth for judge verdicts).
INTENT_MISMATCH = "intent_mismatch"
JUDGE_ERROR = "judge_error"

# Sentinel: a dotted path was absent (distinct from a literal None value).
MISSING = object()


def normalize(value: object) -> str:
    """String-coerce, strip, lowercase -- lenient value comparison so trivial
    formatting differences ('Weekday ' vs 'weekday') do not fail a match."""
    return str(value).strip().lower()


def get_path(obj: Any, dotted: str) -> Any:
    """Read a dotted path (e.g. 'filters.day_type') out of a nested dict.
    Returns MISSING if any segment is absent or a non-dict is traversed."""
    cur = obj
    for seg in dotted.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return MISSING
        cur = cur[seg]
    return cur


@dataclass
class JudgeVerdict:
    passed: bool
    score: float
    tags: list[str] = field(default_factory=list)
    rationale: str = ""


class Judge(ABC):
    @abstractmethod
    def grade(self, *, rubric: dict[str, Any], request: str,
              query: dict[str, Any]) -> JudgeVerdict:
        raise NotImplementedError


class RubricJudge(Judge):
    """Deterministic intent grader. Checks a candidate query against a rubric's
    machine-checkable criteria. No network, no randomness -- so gates and the
    test suite stay hermetic."""

    def grade(self, *, rubric, request, query):
        must_include = rubric.get("must_include", []) or []
        must_exclude = rubric.get("must_exclude", []) or []

        violated = [c for c in must_exclude if self._satisfies(query, c)]
        if violated:
            return JudgeVerdict(False, 0.0, [INTENT_MISMATCH],
                                f"query contains excluded criteria: {violated}")

        unmet = [c for c in must_include if not self._satisfies(query, c)]
        total = len(must_include)
        score = 1.0 if total == 0 else (total - len(unmet)) / total
        if unmet:
            return JudgeVerdict(False, score, [INTENT_MISMATCH],
                                f"query missing required criteria: {unmet}")
        return JudgeVerdict(True, 1.0, [], "all criteria satisfied")

    @staticmethod
    def _satisfies(query: dict, criterion: dict) -> bool:
        actual = get_path(query, criterion["field"])
        if actual is MISSING:
            return False
        if "values" in criterion:
            allowed = {normalize(v) for v in criterion["values"]}
            if isinstance(actual, list):
                return any(normalize(a) in allowed for a in actual)
            return normalize(actual) in allowed
        expected = normalize(criterion["value"])
        if isinstance(actual, list):
            return any(normalize(a) == expected for a in actual)
        return normalize(actual) == expected


class LLMJudge(Judge):
    """Grades intent by a second model call. Injected only for real runs;
    gates and tests use RubricJudge. Fails safe: any provider failure or an
    unparseable / out-of-range verdict is a FAIL tagged JUDGE_ERROR."""

    def __init__(self, provider: Provider, model: str) -> None:
        self._provider = provider
        self._model = model

    def grade(self, *, rubric, request, query):
        prompt = self._build_prompt(rubric, request, query)
        try:
            raw = self._provider.complete(prompt, model=self._model)
        except Exception as e:  # a broken judge must never pass a candidate
            return JudgeVerdict(False, 0.0, [JUDGE_ERROR], f"judge call failed: {e}")
        return self._parse(raw)

    @staticmethod
    def _build_prompt(rubric: dict, request: str, query: dict) -> str:
        return "\n".join([
            "You are grading whether a structured query captures a request's intent.",
            'Return strict JSON only: {"passed": <bool>, "score": <number 0..1>, '
            '"rationale": "<why>"}. No prose outside the JSON.',
            "",
            f"Request: {request}",
            f"Intent criteria: {rubric.get('criteria', '')}",
            f"Candidate query: {json.dumps(query)}",
        ])

    @staticmethod
    def _parse(raw: str) -> JudgeVerdict:
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return JudgeVerdict(False, 0.0, [JUDGE_ERROR], "judge returned non-JSON")
        if not isinstance(obj, dict) or "passed" not in obj or "score" not in obj:
            return JudgeVerdict(False, 0.0, [JUDGE_ERROR], "judge JSON missing fields")
        score = obj["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)) \
                or not (0.0 <= score <= 1.0):
            return JudgeVerdict(False, 0.0, [JUDGE_ERROR],
                                f"judge score out of range: {score!r}")
        passed = bool(obj["passed"])
        return JudgeVerdict(passed, float(score),
                            [] if passed else [INTENT_MISMATCH],
                            str(obj.get("rationale", "")))
