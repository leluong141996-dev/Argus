from core.providers.base import Provider, ProviderError, as_model_call
from core.providers.mock import MockProvider
from core.providers.groq import GroqProvider

__all__ = ["Provider", "ProviderError", "as_model_call", "MockProvider", "GroqProvider", "build_provider"]


def build_provider(name: str, params: dict) -> Provider:
    if name == "mock":
        return MockProvider()
    if name == "groq":
        return GroqProvider(**params)
    raise ProviderError(f"unknown provider {name!r}; known providers: groq, mock")
