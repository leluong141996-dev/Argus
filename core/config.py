"""YAML config → ArgusConfig. Validates required keys and produces one
RunConfig per model for the batch runner."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

from core.runner import RunConfig, new_run_id


class ConfigError(Exception):
    pass


@dataclass
class ProviderConfig:
    name: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArgusConfig:
    task: str
    dataset: str
    models: list[str]
    provider: ProviderConfig
    concurrency: int = 1
    seed: int | None = None
    output: str = "report.json"
    cost_budget_usd: float | None = None
    latency_budget_ms: float | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id:
            self.run_id = new_run_id()

    def run_config_for(self, model: str) -> RunConfig:
        return RunConfig(
            run_id=self.run_id,
            model=model,
            provider=self.provider.name,
            cost_budget_usd=self.cost_budget_usd,
            latency_budget_ms=self.latency_budget_ms,
            seed=self.seed,
        )


def load_config(path: str) -> ArgusConfig:
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except yaml.YAMLError as e:
        raise ConfigError(f"invalid YAML in {path}: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError(f"config must be a mapping, got {type(raw).__name__}")

    for key in ("task", "dataset", "models", "provider"):
        if key not in raw or raw[key] is None:
            raise ConfigError(f"config missing required key: {key!r}")

    prov = raw["provider"]
    if not isinstance(prov, dict) or "name" not in prov:
        raise ConfigError("config 'provider' must be a mapping with a 'name'")

    models = raw["models"]
    if not isinstance(models, list) or not models:
        raise ConfigError("config 'models' must be a non-empty list")

    return ArgusConfig(
        task=raw["task"],
        dataset=raw["dataset"],
        models=models,
        provider=ProviderConfig(name=prov["name"], params=prov.get("params") or {}),
        concurrency=int(raw.get("concurrency", 1)),
        seed=raw.get("seed"),
        output=raw.get("output", "report.json"),
        cost_budget_usd=raw.get("cost_budget_usd"),
        latency_budget_ms=raw.get("latency_budget_ms"),
        run_id=raw.get("run_id"),
    )
