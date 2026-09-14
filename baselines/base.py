"""Baseline shortcut model + expectation contract.

A baseline is a fake model output *strategy*: given a case, it builds a raw
output string (or None when it does not apply to that case). An Expectation
declares what a correct scorer must do with that output — so a gate can
assert the scorer actually catches the shortcut.

Import direction: this module imports only `core.pipeline` (for Stage). It
never imports `plugins/` or `gates/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from core.pipeline import Stage


@dataclass(frozen=True)
class Expectation:
    """What a correct scorer must do with a baseline's output."""

    should_pass: bool                     # True only for oracle/reference outputs
    capped_by: Stage | None = None        # optional: the stage that must cap the row
    require_tags: tuple[str, ...] = ()     # optional: failure tags that must appear


@dataclass(frozen=True)
class Baseline:
    name: str
    build_output: Callable[[dict[str, Any]], str | None]  # case -> fake output, or None to skip
    expect: Expectation
