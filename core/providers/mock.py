"""Deterministic, offline provider for demos, tests, and (later) gates.

Returns a fixed, schema-valid JSON answer so a run produces real records with
no network. It is intentionally task-agnostic: the answer may not be correct
for a given case, but it is always parseable."""
from __future__ import annotations

import json

from core.providers.base import Provider

_FIXED_ANSWER = json.dumps(
    {
        "claims": {"weekday_commute": "likely_home_to_office_commute"},
        "evidence_ids": ["e1", "e2"],
        "confidence": 0.9,
        "action": "suggest_commute_pass",
    }
)


class MockProvider(Provider):
    def complete(self, prompt: str, *, model: str) -> str:
        return _FIXED_ANSWER
