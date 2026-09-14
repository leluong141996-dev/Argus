# tests/test_config.py
from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import load_config, ConfigError  # noqa: E402


def _write(tmp_path, text):
    p = tmp_path / "c.yaml"
    p.write_text(text)
    return str(p)


VALID = """
task: agent_reasoning
dataset: datasets/teaching/agent_reasoning/cases.json
models: [openai/gpt-oss-120b]
provider:
  name: groq
  params: {temperature: 0}
concurrency: 3
output: out.json
"""


def test_load_config_parses_all_fields(tmp_path):
    cfg = load_config(_write(tmp_path, VALID))
    assert cfg.task == "agent_reasoning"
    assert cfg.models == ["openai/gpt-oss-120b"]
    assert cfg.provider.name == "groq"
    assert cfg.provider.params == {"temperature": 0}
    assert cfg.concurrency == 3
    assert cfg.output == "out.json"


def test_run_config_for_builds_runconfig_per_model(tmp_path):
    cfg = load_config(_write(tmp_path, VALID))
    rc = cfg.run_config_for("openai/gpt-oss-120b")
    assert rc.model == "openai/gpt-oss-120b"
    assert rc.provider == "groq"
    assert rc.run_id  # auto-generated, non-empty


def test_missing_required_key_raises_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, "task: agent_reasoning\n"))  # no dataset/models/provider
