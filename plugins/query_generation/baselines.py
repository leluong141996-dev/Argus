"""Contract-specific shortcut baselines for `query_generation`.

Baselines are implemented in Task 5; Task 4 registers the plugin with an empty
baseline set.
"""

from __future__ import annotations

from baselines.base import Baseline


def contract_baselines() -> list[Baseline]:
    return []
