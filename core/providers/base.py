"""Provider abstraction. A provider turns a prompt into text; the runner never
knows which one it is talking to. Cost/latency stay runner-owned, so a provider
only returns text -- token accounting is out of scope for M1 (see spec)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class ProviderError(Exception):
    pass


class Provider(ABC):
    @abstractmethod
    def complete(self, prompt: str, *, model: str) -> str:
        raise NotImplementedError


def as_model_call(provider: Provider, model: str) -> Callable[[str], str]:
    """Adapt a Provider to the `str -> str` callable the plugin contract expects."""
    return lambda prompt: provider.complete(prompt, model=model)
