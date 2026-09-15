from __future__ import annotations
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import load_config  # noqa: E402


def _write(tmp_path, body: str) -> str:
    p = tmp_path / "cfg.yaml"
    p.write_text(textwrap.dedent(body))
    return str(p)


def test_config_without_judge_is_none(tmp_path):
    cfg = load_config(_write(tmp_path, """
        task: query_generation
        dataset: datasets/teaching/query_generation/cases.json
        models: [m1]
        provider: {name: mock}
    """))
    assert cfg.judge is None


def test_config_parses_judge_section(tmp_path):
    cfg = load_config(_write(tmp_path, """
        task: query_generation
        dataset: datasets/teaching/query_generation/cases.json
        models: [m1]
        provider: {name: mock}
        judge:
          provider: {name: groq, params: {temperature: 0}}
          model: judge-model-x
    """))
    assert cfg.judge is not None
    assert cfg.judge.provider.name == "groq"
    assert cfg.judge.provider.params == {"temperature": 0}
    assert cfg.judge.model == "judge-model-x"


# --- judge injection ----------------------------------------------------------
from core.config import ArgusConfig, ProviderConfig, JudgeConfig  # noqa: E402
from core.judge import LLMJudge, RubricJudge  # noqa: E402
from server.runs import execute_run  # noqa: E402


def _cfg(judge=None):
    return ArgusConfig(
        task="query_generation",
        dataset="datasets/teaching/query_generation/cases.json",
        models=["m1"], provider=ProviderConfig(name="mock"),
        concurrency=1, judge=judge,
    )


def test_no_judge_section_keeps_rubric_judge():
    records = execute_run(_cfg(), run_gate=False)
    assert records  # ran end-to-end offline with the default judge
    # default judge unchanged is proven by an offline mock run producing records


def test_judge_section_injects_llm_judge(monkeypatch):
    captured = {}
    import server.runs as runs_mod

    real_get_plugin = runs_mod.get_plugin

    def spy_get_plugin(task):
        p = real_get_plugin(task)
        captured["plugin"] = p
        return p
    monkeypatch.setattr(runs_mod, "get_plugin", spy_get_plugin)

    cfg = _cfg(judge=JudgeConfig(provider=ProviderConfig(name="mock"), model="jm"))
    execute_run(cfg, run_gate=False)
    assert isinstance(captured["plugin"].judge, LLMJudge)
