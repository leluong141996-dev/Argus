"""Embed a report.json into the dashboard template -> index.html.

Maintainer-only build step. The end user just opens index.html.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REGION = re.compile(
    r"/\*__ARGUS_REPORT__\*/.*?/\*__END_REPORT__\*/",
    re.DOTALL,
)
_REPLACEMENT = "/*__ARGUS_REPORT__*/ {json} /*__END_REPORT__*/"


def embed_report(template: str, report_json: str) -> str:
    if not _REGION.search(template):
        raise ValueError("template missing /*__ARGUS_REPORT__*/ ... /*__END_REPORT__*/ marker")
    # Prevent an embedded "</script>" (or any "</") in string data from
    # closing the inline <script> tag early.
    safe = report_json.replace("</", "<\\/")
    # re.sub gives backslashes special meaning in the replacement string, so
    # pass a function that returns the literal text.
    return _REGION.sub(lambda _m: _REPLACEMENT.format(json=safe), template, count=1)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Embed a report.json into the dashboard template.")
    p.add_argument("report", help="path to report.json")
    p.add_argument("--template", default="dashboards/web/template.html")
    p.add_argument("--out", default="dashboards/web/index.html")
    args = p.parse_args(argv)
    try:
        template = Path(args.template).read_text()
        report_json = Path(args.report).read_text()
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    try:
        html = embed_report(template, report_json)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    Path(args.out).write_text(html)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
