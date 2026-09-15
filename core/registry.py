"""Maps a task name (as used in a config file) to its plugin class.

Adding a new benchmark surface means registering it here; the runner and CLI
never hardcode a task name.
"""
from __future__ import annotations

from plugins.agent_reasoning.plugin import AgentReasoningPlugin
from plugins.agentic_coding.plugin import AgenticCodingPlugin
from plugins.tool_use.plugin import ToolUsePlugin
from plugins.multimodal_matching.plugin import MultimodalMatchingPlugin
from plugins.query_generation.plugin import QueryGenerationPlugin
from plugins.base import TaskPlugin

PLUGINS: dict[str, type[TaskPlugin]] = {
    "agentic_coding": AgenticCodingPlugin,
    "agent_reasoning": AgentReasoningPlugin,
    "multimodal_matching": MultimodalMatchingPlugin,
    "query_generation": QueryGenerationPlugin,
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
