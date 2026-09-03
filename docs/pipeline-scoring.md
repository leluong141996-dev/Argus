# Pipeline-style scoring

## The problem with one number

A single pass/fail score tells you *that* a model failed a case, not *where*.
Two rows with the same score can fail for completely different reasons: one
model fabricated an evidence ID, another cited real evidence but drew the
wrong conclusion from it, another reasoned correctly but recommended an
action outside the allowed set. Collapsing all of that into one number
throws away exactly the information an engineer needs to fix a prompt, a
scorer, a dataset, or a model choice.

Pipeline-style scoring keeps the answer's final output as-is, but stops
scoring it as a single unit. Instead, each case/model pair is scored as a
sequence of independent **stages**, and every stage produces its own
verdict.

## The stage taxonomy

```python
class Stage(str, Enum):
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    ACTION_SELECTION = "action_selection"
    SAFETY = "safety"
    COST = "cost"
    LATENCY = "latency"
```

A task plugin declares the subset of stages that apply to it via
`STAGES: tuple[Stage, ...]`. Not every task has every stage — a tool-calling
task has no `RETRIEVAL` stage; a pure code-diff task has no
`ACTION_SELECTION` stage. There's no requirement to use all six; the
taxonomy is a shared vocabulary, not a checklist every plugin must fill in.

### Runner-owned vs. plugin-owned stages

`COST` and `LATENCY` are **never** implemented by a plugin. The runner
measures wall-clock time around `plugin.generate()` and reads token counts
back from the result, then scores both stages itself (`core/cost.py`,
`core/latency.py`). This is deliberate: pricing tables and latency budgets
are operational concerns that apply uniformly across every task, and a
plugin author should never have to think about them. `TaskPlugin.validate_stages()`
raises at validation time if a plugin tries to claim either one.

`RETRIEVAL`, `REASONING`, `ACTION_SELECTION`, and `SAFETY` are always
plugin-owned, because what counts as "supported by evidence" or "a safe
action" is entirely task-specific.

## How a row gets capped

A `StageResult` carries a `passed: bool` verdict that is independent of its
numeric `score`. A stage can be:

- **Informational** (`weight=0.0`) — contributes a score but never fails the
  row on its own. `COST` and `LATENCY` default to this when no budget is
  configured.
- **Gating** (`weight>0.0`, the default for every plugin-owned stage) — a
  failed gating stage sets `PipelineScore.capped_by` to that stage's name.

The runner picks the *first* failing gating stage, in the order the plugin
returned its stages, followed by `COST` then `LATENCY`. This keeps capping
deterministic and traceable: `record.pipeline.capped_by` always tells you
exactly which stage decided the row's fate, instead of leaving it to guess
from a blended number.

```python
all_stages = [*task_stages, cost_stage, latency_stage]
capped_by = next((s.stage.value for s in all_stages if not s.passed and s.weight > 0), None)
```

## What replaces "the score"

`RowRecord` has no authoritative single score. `record.legacy_score` exists
purely for tools that still want to sort by one number (a quick CLI
printout, a rough leaderboard view) — it's a weighted mean over the stages,
computed on demand, and nothing in the scoring logic is allowed to depend on
it. The row's ground truth is `record.pipeline.stages`.

Aggregation follows the same rule: `dashboards/aggregate.summarize()`
produces one `StageSummary` per `(task, model, stage)` triple. It never
folds stages together and never folds tasks together. A setting that helps
`reasoning` on one task can hurt `retrieval` on another — a single global
ranking would hide exactly that.

## Writing a stage-aware plugin

1. Subclass `TaskPlugin`, set `name` and `STAGES` (only the stages that
   apply, excluding `COST`/`LATENCY`).
2. Implement `generate(case, model_call) -> GenerationResult` — request
   shaping and response parsing, same as before.
3. Implement `score(case, result) -> list[StageResult]` — return **exactly**
   one `StageResult` per stage in `STAGES`. The runner calls
   `_validate_stage_coverage` after every `score()` call and raises loudly
   if a stage goes missing — a plugin can't silently drop a stage it
   promised to score.
4. Don't compute cost or latency. The runner appends both automatically.

See `plugins/agent_reasoning/plugin.py` for a full reference implementation,
and `tests/test_pipeline_scoring.py` for the behavior it's expected to
guarantee — including that a shortcut like citing the entire evidence ledger
is caught at the `retrieval` stage without being allowed to hide behind a
correct final claim.

## Next steps

- Migrate `tool_use` to declare `STAGES=(Stage.ACTION_SELECTION,)`, treating
  tool-name selection as `ACTION_SELECTION` and parameter correctness as a
  tag within that stage.
- Migrate `agentic_coding` to a richer stage set: `REASONING` (plan quality),
  `ACTION_SELECTION` (which files/functions were touched), `SAFETY`
  (hard-failure and anti-gaming checks), with visible/hidden test results
  feeding into `REASONING` and `ACTION_SELECTION` respectively.
- Add a `configs/pricing.yaml` loader so `core/cost.py` stops relying on the
  built-in `DEFAULT_PRICING` table for anything beyond the demo.
- Add per-stage weight overrides to `RunConfig` so a report can be generated
  with different stage priorities without touching plugin code.
