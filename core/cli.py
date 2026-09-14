"""`argus` command-line entry point. M1 `run`; M2 trust gates."""
from __future__ import annotations

import argparse
import os
import sys

from core.config import load_config, ConfigError
from core.dataset import load_cases, DatasetError
from core.providers import build_provider, ProviderError, as_model_call
from core.registry import get_plugin, UnknownTaskError
from core.report_io import write_records
from core.runner import run_batch
from gates import GateReport, run_gates


def _load_canary(task: str) -> list:
    path = f"datasets/canary/{task}/cases.json"
    if not os.path.exists(path):
        return []
    return load_cases(path)


def _print_gate_report(report: GateReport) -> None:
    for r in report.results:
        for c in r.checks:
            status = "OK" if c.passed else "MISMATCH"
            print(f"[{r.name}] {c.name}: {status} — {c.detail}")
    print(f"gate: {'PASS' if report.passed else 'FAIL'}")


def _print_gate_failures(report: GateReport) -> None:
    print("error: trust gate failed — run blocked (eval not trustworthy):")
    for r in report.results:
        for c in r.checks:
            if not c.passed:
                print(f"  [{r.name}] {c.name}: {c.detail}")


def _run(args: argparse.Namespace) -> int:
    try:
        cfg = load_config(args.config)
        plugin = get_plugin(cfg.task)
        cases = load_cases(cfg.dataset)
        canary_cases = _load_canary(cfg.task)
    except (ConfigError, DatasetError, UnknownTaskError) as e:
        print(f"error: {e}")
        return 1

    gate_template = cfg.run_config_for("baseline")

    if args.baselines_only:
        report = run_gates(plugin, cases, canary_cases, gate_template)
        _print_gate_report(report)
        return 0 if report.passed else 3

    if args.no_gate:
        print("warning: --no-gate set; skipping trust gate pre-flight")
    else:
        report = run_gates(plugin, cases, canary_cases, gate_template)
        if not report.passed:
            _print_gate_failures(report)
            return 3

    try:
        provider = build_provider(cfg.provider.name, cfg.provider.params)
        model_calls = {m: as_model_call(provider, m) for m in cfg.models}
        run_configs = {m: cfg.run_config_for(m) for m in cfg.models}
        records = run_batch(plugin, cases, model_calls, run_configs, cfg.concurrency)
    except (ConfigError, DatasetError, ProviderError, UnknownTaskError) as e:
        print(f"error: {e}")
        return 1

    out = args.out or cfg.output
    write_records(records, out)
    skipped = sum(1 for r in records if r.skip_reason)
    print(f"{len(records)} records → {out} "
          f"(task={cfg.task}, models={','.join(cfg.models)}, skipped={skipped})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="argus")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="run a task against providers from a config")
    run_p.add_argument("--config", required=True)
    run_p.add_argument("--out", default=None, help="override config.output")
    run_p.add_argument("--baselines-only", action="store_true",
                       help="run only the trust-gate suite (baselines + canaries)")
    run_p.add_argument("--no-gate", action="store_true",
                       help="skip the trust-gate pre-flight before a normal run")
    run_p.set_defaults(func=_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
