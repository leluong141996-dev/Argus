"""Gate result dataclasses + the expectation-matching logic.

Matching compares a produced RowRecord against a baseline/canary Expectation
and returns (matched, human-readable detail). The detail always spells out
expected-vs-actual so a MISMATCH is debuggable from the console alone.
"""

from __future__ import annotations

from dataclasses import dataclass

from baselines.base import Expectation
from core.record_schema import RowRecord


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class GateResult:
    name: str  # "baselines" | "canary"
    checks: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


@dataclass(frozen=True)
class GateReport:
    results: list[GateResult]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)


def match_expectation(record: RowRecord, expect: Expectation) -> tuple[bool, str]:
    ps = record.pipeline
    failing = [s.stage.value for s in ps.stages if not s.passed and s.weight > 0]
    capped = ps.capped_by
    tags = record.failure_tags

    if expect.should_pass:
        if capped is None and not failing:
            return True, "expected PASS -> PASS"
        return False, f"expected PASS but capped_by={capped}, failing={failing}, tags={tags}"

    if not failing:
        return False, "expected FAIL but every weighted stage passed"
    if expect.capped_by is not None and capped != expect.capped_by.value:
        return False, f"expected FAIL capped_by={expect.capped_by.value} but capped_by={capped}"
    missing = [t for t in expect.require_tags if t not in tags]
    if missing:
        return False, f"expected tags {list(expect.require_tags)} but missing {missing} (tags={tags})"

    exp_cap = expect.capped_by.value if expect.capped_by else "any"
    return True, f"expected FAIL (capped_by={exp_cap}) -> FAIL capped_by={capped}, tags={tags}"
