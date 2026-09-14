from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.providers.base import as_model_call  # noqa: E402
from core.providers.mock import MockProvider  # noqa: E402


def test_mock_provider_is_deterministic():
    p = MockProvider()
    a = p.complete("same prompt", model="m")
    b = p.complete("same prompt", model="m")
    assert a == b


def test_mock_provider_returns_parseable_json():
    import json
    out = MockProvider().complete("anything", model="m")
    assert json.loads(out)  # does not raise


def test_as_model_call_wraps_provider_into_str_callable():
    call = as_model_call(MockProvider(), "m")
    assert isinstance(call("hi"), str)
