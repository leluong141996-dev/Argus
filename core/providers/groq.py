"""Groq adapter (OpenAI-compatible chat completions).

One POST to /chat/completions. The httpx client is injectable so tests can run
with no network. Real token usage from the response is intentionally not
plumbed into scoring in M1 (see spec)."""
from __future__ import annotations

import os
import httpx

from core.providers.base import Provider, ProviderError


class GroqProvider(Provider):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1",
        temperature: float = 0.0,
        max_tokens: int = 512,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("GROQ_API_KEY")
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = client or httpx.Client(timeout=timeout)

    def complete(self, prompt: str, *, model: str) -> str:
        if not self._api_key:
            raise ProviderError("GROQ_API_KEY is not set")
        try:
            resp = self._client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self._temperature,
                    "max_tokens": self._max_tokens,
                },
            )
        except httpx.HTTPError as e:
            raise ProviderError(f"Groq request failed: {e}") from e

        if resp.status_code != 200:
            raise ProviderError(f"Groq returned {resp.status_code}: {resp.text[:200]}")
        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise ProviderError(f"unexpected Groq response shape: {e}") from e
