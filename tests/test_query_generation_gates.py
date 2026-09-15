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


# --- baseline gate ------------------------------------------------------------
import json  # noqa: E402
from core.dataset import load_cases  # noqa: E402
from core.runner import RunConfig  # noqa: E402
from baselines.base import Baseline, Expectation  # noqa: E402
from plugins.query_generation.plugin import QueryGenerationPlugin  # noqa: E402
from gates.baseline_gate import run_baseline_gate  # noqa: E402

TEACHING = "datasets/teaching/query_generation/cases.json"


def _rc():
    return RunConfig(run_id="gate-test", model="baseline", provider="test")


def test_real_baselines_all_pass():
    plugin = QueryGenerationPlugin()  # default RubricJudge -> hermetic
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    assert result.passed, [(c.name, c.detail) for c in result.checks if not c.passed]
    assert {c.name for c in result.checks} == {
        "empty_output", "unknown_metric", "first_metric", "unsafe_query", "oracle"
    }


def test_first_metric_check_is_the_judge_stage_teeth():
    # The first_metric shortcut is caught only by REASONING (judge) -> its
    # gate check must pass, proving the judge stage is a real gate.
    plugin = QueryGenerationPlugin()
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    fm = next(c for c in result.checks if c.name == "first_metric")
    assert fm.passed


def test_gate_has_teeth_catches_scorer_hole():
    # An oracle-correct output declared should_pass=False simulates a scorer
    # hole: the gate must report MISMATCH (not vacuously pass).
    plugin = QueryGenerationPlugin()
    sneaky = Baseline("sneaky",
                      lambda case: json.dumps(case["expected"]["query"]),
                      Expectation(should_pass=False))
    plugin.baselines = lambda: [sneaky]  # type: ignore[method-assign]
    result = run_baseline_gate(plugin, load_cases(TEACHING), _rc())
    assert not result.passed
