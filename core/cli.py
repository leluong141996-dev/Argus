"""`argus` command-line entry point. M1 implements `run`."""
from __future__ import annotations

import argparse
import sys

from core.config import load_config, ConfigError
from core.dataset import load_cases, DatasetError
from core.providers import build_provider, ProviderError, as_model_call
from core.registry import get_plugin, UnknownTaskError
from core.report_io import write_records
from core.runner import run_batch


def _run(args: argparse.Namespace) -> int:
    if args.baselines_only:
        print("error: --baselines-only is planned for M2 and not implemented yet")
        return 2
    try:
        cfg = load_config(args.config)
        plugin = get_plugin(cfg.task)
        cases = load_cases(cfg.dataset)
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
    run_p.add_argument("--baselines-only", action="store_true")
    run_p.set_defaults(func=_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
