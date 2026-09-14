# tests/test_groq_provider.py
from __future__ import annotations
import sys
from pathlib import Path
import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.providers.groq import GroqProvider  # noqa: E402
from core.providers import build_provider  # noqa: E402
from core.providers.base import ProviderError  # noqa: E402


def _client_returning(payload: dict, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_groq_parses_message_content():
    payload = {"choices": [{"message": {"content": "hello-out"}}]}
    p = GroqProvider(api_key="k", client=_client_returning(payload))
    assert p.complete("hi", model="openai/gpt-oss-120b") == "hello-out"


def test_groq_missing_key_raises_provider_error():
    p = GroqProvider(api_key=None, client=_client_returning({}))
    with pytest.raises(ProviderError):
        p.complete("hi", model="m")


def test_groq_non_200_raises_provider_error():
    p = GroqProvider(api_key="k", client=_client_returning({"error": "bad"}, status=400))
    with pytest.raises(ProviderError) as exc:
        p.complete("hi", model="m")
    assert "400" in str(exc.value)


def test_build_provider_selects_groq():
    assert isinstance(build_provider("groq", {"api_key": "k"}), GroqProvider)
