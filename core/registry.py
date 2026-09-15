"""Maps a task name (as used in a config file) to its plugin class.

Adding a new benchmark surface means registering it here; the runner and CLI
never hardcode a task name.
"""
from __future__ import annotations

from plugins.agent_reasoning.plugin import AgentReasoningPlugin
from plugins.tool_use.plugin import ToolUsePlugin
from plugins.base import TaskPlugin

PLUGINS: dict[str, type[TaskPlugin]] = {
    "agent_reasoning": AgentReasoningPlugin,
    "tool_use": ToolUsePlugin,
}


class UnknownTaskError(Exception):
    pass


def get_plugin(task: str) -> TaskPlugin:
    try:
        return PLUGINS[task]()
    except KeyError:
        known = ", ".join(sorted(PLUGINS)) or "(none)"
        raise UnknownTaskError(f"unknown task {task!r}; known tasks: {known}") from None
