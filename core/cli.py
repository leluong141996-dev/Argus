"""`argus` command-line entry point. M1 `run`; M2 trust gates."""
from __future__ import annotations

import argparse
import sys

from core.config import load_config, ConfigError
from core.dataset import load_cases, DatasetError
from core.providers import ProviderError
from core.registry import get_plugin, UnknownTaskError
from core.report_io import write_records
from gates import GateReport, run_gates
from server.runs import execute_run, GateAborted, _load_canary


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


def _serve(args: argparse.Namespace) -> int:
    import uvicorn
    from server.app import create_app
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def _run(args: argparse.Namespace) -> int:
    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(f"error: {e}")
        return 1

    if args.baselines_only:
        try:
            plugin = get_plugin(cfg.task)
            cases = load_cases(cfg.dataset)
            canary_cases = _load_canary(cfg.task)
        except (ConfigError, DatasetError, UnknownTaskError) as e:
            print(f"error: {e}")
            return 1
        gate_template = cfg.run_config_for("baseline")
        report = run_gates(plugin, cases, canary_cases, gate_template)
        _print_gate_report(report)
        return 0 if report.passed else 3

    if args.no_gate:
        print("warning: --no-gate set; skipping trust gate pre-flight")
    try:
        records = execute_run(cfg, run_gate=not args.no_gate)
    except GateAborted as e:
        _print_gate_failures(e.report)
        return 3
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

    serve_p = sub.add_parser("serve", help="run the ARGUS web app (API + UI)")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.set_defaults(func=_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
