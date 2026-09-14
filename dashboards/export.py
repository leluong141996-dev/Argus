"""Export row records to a report.json the web dashboard loads.

The dashboard consumes the exact M1 report shape, so this delegates to
write_records -- there is deliberately no second format to drift from.
"""
from __future__ import annotations

from core.record_schema import RowRecord
from core.report_io import write_records


def export_report(records: list[RowRecord], path: str) -> None:
    write_records(records, path)
