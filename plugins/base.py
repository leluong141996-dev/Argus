"""Base interface every task plugin implements.

The runner (core/runner.py) owns execution: it calls `generate`, times it,
counts tokens, and appends the COST/LATENCY stages itself. A plugin only
ever implements `score`, and only for the task-specific stages it declares
in `STAGES`. This keeps the boundary from the harness's design intact: the
runner stays shared and boring, the plugin owns request shaping, response
parsing, and the scoring contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from core.pipeline import RUNNER_OWNED_STAGES, Stage, StageResult

if TYPE_CHECKING:
    from baselines.base import Baseline


@dataclass
class GenerationResult:
    """What a plugin's `generate` returns after calling the model under test."""

    raw_output: str
    parsed_output: dict[str, Any] | None
    tokens_in: int
    tokens_out: int


class TaskPlugin(ABC):
    """Contract every ARGUS task plugin must satisfy.

    STAGES declares which task-specific pipeline stages this plugin scores.
    It must be a subset of Stage minus the runner-owned stages (COST,
    LATENCY) -- a plugin that tries to claim those raises at validation time.
    """

    name: str
    STAGES: tuple[Stage, ...] = ()

    @abstractmethod
    def generate(self, case: dict[str, Any], model_call: Any) -> GenerationResult:
        """Shape the request for `case`, call `model_call`, parse the response."""
        raise NotImplementedError

    @abstractmethod
    def score(self, case: dict[str, Any], result: GenerationResult) -> list[StageResult]:
        """Score every stage declared in `self.STAGES` for this case/output
        pair. Must return exactly one StageResult per declared stage -- the
        runner validates coverage and fails loudly if a plugin silently
        drops a stage (see core/runner.py: _validate_stage_coverage)."""
        raise NotImplementedError

    def baselines(self) -> list["Baseline"]:
        """Shortcut baselines whose Expectations the eval must satisfy.

        Optional and additive: default is none. A plugin opts in by returning
        generic + task-specific baselines. Existing plugins, run_case, and
        run_batch are unaffected.
        """
        return []

    @classmethod
    def validate_stages(cls) -> None:
        overlap = set(cls.STAGES) & RUNNER_OWNED_STAGES
        if overlap:
            raise TypeError(
                f"{cls.__name__} declares runner-owned stage(s) "
                f"{sorted(s.value for s in overlap)}; COST and LATENCY are "
                "always computed by the runner, not by plugins."
            )
