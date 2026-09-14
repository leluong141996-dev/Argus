from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.registry import get_plugin, UnknownTaskError  # noqa: E402
from plugins.agent_reasoning.plugin import AgentReasoningPlugin  # noqa: E402


def test_get_plugin_returns_instance_for_known_task():
    plugin = get_plugin("agent_reasoning")
    assert isinstance(plugin, AgentReasoningPlugin)


def test_get_plugin_raises_with_helpful_message_for_unknown_task():
    with pytest.raises(UnknownTaskError) as exc:
        get_plugin("does_not_exist")
    assert "agent_reasoning" in str(exc.value)  # lists known tasks
