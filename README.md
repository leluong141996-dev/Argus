<p align="center">
  <img src="./argus-logo.png" alt="ARGUS logo" width="180"/>
</p>

<h1 align="center">ARGUS</h1>

<p align="center">
  <b>An open-source benchmark and evaluation platform for AI agents.</b><br/>
  Measure reasoning, planning, tool use, reliability, safety, cost, and real-world task performance.
</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue.svg"/>
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-orange.svg"/>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue.svg"/>
  <img alt="PRs" src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg"/>
</p>

---

## Why ARGUS

Public leaderboards are good at telling you which model *looks* strong. They are not good at catching the quiet failures that break production systems: a right-shaped SQL query that quietly swaps the metric, a tool call that picks the right tool but drifts on parameters, an agent that cites every piece of evidence instead of only what supports its claim, or a coding patch that passes every visible test while breaking an invariant nobody wrote a test for.

**ARGUS exists to catch the plausible-but-wrong answer, not just the obviously-wrong one.**

It is a configurable evaluation harness for AI agents and models. It runs providers through **task plugins**, each with its own scoring contract, records one row per case/model pair, and scores with deterministic checkers or LLM judges depending on what the task actually needs. ARGUS treats evaluation like software: versioned, baseline-tested, gated, and built so failure modes are visible enough for a team to debug — not just a leaderboard number.

## Core philosophy

1. **Cases should be realistic, not generic.** Good eval cases include distractors, stale context, ambiguous evidence, and the boundary conditions that make real work hard — without depending on real production data. Synthetic and redacted cases keep the *shape* of the difficulty without exposing the underlying system.
2. **Score the contract, not the vibe.** LLM judges are reserved for genuinely open-ended tasks. Wherever a task has a checkable contract — a schema, a canonical tool signature, a set of valid evidence IDs, a test suite — ARGUS scores it deterministically. A fluent answer that violates the contract should not get credit.
3. **Make shortcuts visible.** Every task ships with adversarial baselines — empty output, schema-only output, cite-everything output, no-op agents, reference agents — that exist to break the scorer, not to pad a leaderboard. If a shortcut baseline can pass, the eval isn't ready.

## How it works
<p align="center">
  <img src="./argus-how-it-works.png" alt="ARGUS logo"/>
</p>

The harness itself is intentionally boring: it loads config, checks compatibility, calls a plugin, writes a record. All the interesting behavior — what counts as correct, what counts as a shortcut, how to score it — lives inside the task plugin. Adding a new benchmark surface means writing a new plugin, not touching the core.

## Task plugins

| Plugin | What the contract protects | Scoring |
|---|---|---|
| `query_generation` | Metric intent and schema intent under paraphrase/pressure | LLM judge (business intent is open-ended) |
| `tool_use` | Canonical tool selection and parameter correctness | Deterministic |
| `multimodal_matching` | Constrained decisions over paired multimodal input | Deterministic (exact label match) |
| `agent_reasoning` | Grounded claims, evidence faithfulness, calibrated confidence, safe actions | Deterministic (schema validity, claim correctness, evidence ID faithfulness, calibration, action quality, safety) |
| `agentic_coding` | Repository-level behavior beyond visible tests | Visible + hidden tests, hard-failure gates, anti-gaming checks |

Each plugin defines:
- **Case format** — the input contract (e.g. a synthetic evidence ledger, a repo diff task, a tool-call context).
- **Ontology / contract** — the set of valid claims, tools, labels, or invariants a correct answer must respect.
- **Scorer** — deterministic checks where possible, LLM judge only where the task is genuinely open-ended.
- **Baselines** — shortcut strategies the scorer must correctly reject.

### Example: `agent_reasoning`

Each case is a synthetic evidence ledger (events, actions, noise, distractors) with no real user data. The agent must return strict, schema-valid output. Claims must come from a fixed ontology; every cited evidence ID must exist; weak or sensitive inferences must be suppressed rather than stated with false confidence. The scorer distinguishes **required claims**, **acceptable auxiliary claims**, and **forbidden claims**, so an agent can get credit for useful extra findings without getting a pass on unsafe or unsupported ones. A row that cites every event, fabricates an evidence ID, or proposes an unsafe action gets an explicit failure tag or a score cap — not just a lower number.

### Example: `agentic_coding`

The target repository is synthetic but the task is real-shaped: a cross-cutting change touching API compatibility, background workers, event emission, rollout flags, migrations, idempotency, and concurrency. Passing the visible test suite is necessary but not sufficient — hidden tests protect invariants the prompt never mentions.

## Design principles in practice

- **Deterministic-first scoring.** LLM judges are the exception, used only when correctness genuinely depends on open-ended intent (e.g. SQL). Everywhere else, scoring is a checkable function of the output.
- **Shortcut baselines as first-class citizens.** Every task plugin ships baselines whose entire purpose is to fail: empty output, schema-only output, cite-all-evidence, unsafe-sensitive output, no-op coding agent, and a reference/oracle agent. These run before any real comparison is trusted.
- **Teaching vs. certification split.** One dataset can't be fully open *and* fully overfit-resistant. ARGUS separates:
  - **Teaching artifacts** — shared examples, task contracts, scorers, baselines, canaries. Public, used to learn the method.
  - **Certification artifacts** — hidden splits, seeds, raw outputs, full comparison evidence. Access-controlled, used to check generalization.
- **Gates before trust.** Before a comparison run counts, it must pass:
  1. Oracle/reference solutions behave as expected.
  2. Weak baselines fail.
  3. Redaction passes where applicable.
  4. Score spread remains meaningful (not degenerate).
  5. Canaries (deliberately simple/malformed cases with a known expected result) catch harness regressions.

## Row-level records

The leaderboard number answers *which model wins*. It doesn't answer *why*. Every run writes one record per case/model pair with the fields that make debugging and reruns possible:

```json
{
  "case_id": "argus-reason-0417",
  "task": "agent_reasoning",
  "model": "provider/model-name",
  "provider": "provider-name",
  "score": 0.62,
  "score_cap_applied": true,
  "failure_tags": ["cite_all_evidence", "unsupported_claim"],
  "raw_output": "...",
  "parsed_output": { "...": "..." },
  "tokens_in": 1834,
  "tokens_out": 412,
  "latency_ms": 2140,
  "judge_latency_ms": null,
  "skip_reason": null,
  "resolved_config": { "...": "..." },
  "seed": 7,
  "run_id": "2026-09-03T10-22-00Z",
  "harness_version": "0.3.0"
}
```

Model summaries (dashboard-ready aggregates) are derived from these rows, never the other way around — the row is the source of truth.

## What ARGUS is *not*

- **Not proof of production uplift.** Synthetic evals tell you whether a model respects a contract under controlled pressure. Live retrieval quality, real user impact, and rollout decisions need separate evidence.
- **Not a single global score.** Different tasks reward different behavior — more reasoning can help planning-heavy tool use and hurt tasks that need literal schema discipline. ARGUS reports at the task/category level with failure tags, not one universal ranking.
- **Not a place to reward fluency.** A plausible answer that fails the contract is a failure, full stop, regardless of how confident or well-formatted it looks.

## Project structure

```
argus/
├── configs/                  # YAML: providers, models, task settings, judge, output
├── core/
│   ├── runner.py              # loads cases, checks modality/API support, dispatches to plugins
│   ├── record_schema.py       # row-level record + model summary schema
│   └── providers/             # model provider adapters
├── plugins/
│   ├── query_generation/
│   ├── tool_use/
│   ├── multimodal_matching/
│   ├── agent_reasoning/
│   └── agentic_coding/
├── datasets/
│   ├── teaching/               # public examples, contracts, canaries
│   └── certification/          # hidden splits, access-controlled
├── baselines/                  # shortcut baselines per task
├── gates/                      # oracle / weak-baseline / redaction / canary checks
├── dashboards/                 # aggregation + reporting
└── argus-logo.png
```

## Quick start

```bash
git clone https://github.com/<your-org>/argus.git
cd argus
pip install -r requirements.txt

# Run a task against one or more providers defined in the config
argus run --config configs/agent_reasoning.yaml

# Run the shortcut baselines to sanity-check the scorer before trusting results
argus run --config configs/agent_reasoning.yaml --baselines-only

# Generate a dashboard from the latest run
argus report --run-id <run_id>
```

> ARGUS is early-stage. Interfaces, config schema, and plugin APIs may change between minor versions.

## Roadmap

- [ ] Pipeline-style scoring: separate retrieval, reasoning, action selection, latency, cost, and safety instead of scoring only the final answer.
- [ ] More task plugins contributed by the community (RAG faithfulness, multi-turn tool orchestration, long-horizon agent planning).
- [ ] Standardized canary suite shared across all plugins.
- [ ] Public dashboard template for reporting task-level results (not a single global leaderboard).
- [ ] Plugin authoring guide + cookiecutter template so new benchmark surfaces don't require touching core.

## Contributing

Contributions are welcome — especially new task plugins, shortcut baselines for existing tasks, and canary cases that catch real harness bugs. Please open an issue describing the contract your plugin protects before submitting a large PR: a plugin without a clear "what does correct mean here" is hard to review.

## License

MIT — see [LICENSE](./LICENSE).

## Acknowledgments

The core design ideas — task-owned scoring contracts, deterministic-first scoring, shortcut baselines as first-class tests, and the teaching/certification split — are adapted from Grab's engineering write-up on their internal [Grab Bench](https://engineering.grab.com/grab-bench-evaluating-ai) evaluation harness. ARGUS reimplements these ideas as a general-purpose, open-source platform for AI agent evaluation.