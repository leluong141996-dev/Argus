"""SQLite run-metadata store. Stdlib only — no FastAPI import here.

Detailed per-row results live in runs/<run_id>/report.json; this table only
holds the metadata needed to list/filter/sort runs quickly."""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id      TEXT PRIMARY KEY,
  task        TEXT NOT NULL,
  models      TEXT NOT NULL,
  provider    TEXT NOT NULL,
  config      TEXT NOT NULL,
  status      TEXT NOT NULL,
  total       INTEGER,
  passed      INTEGER,
  failed      INTEGER,
  report_path TEXT,
  error       TEXT,
  created_at  TEXT NOT NULL,
  finished_at TEXT
);
"""


def default_db_path() -> str:
    return os.environ.get("ARGUS_DB", "argus.db")


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RunMeta:
    run_id: str
    task: str
    models: list[str]
    provider: str
    config: str
    created_at: str


class RunStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def insert_running(self, meta: RunMeta) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO runs (run_id, task, models, provider, config, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'running', ?)",
                (meta.run_id, meta.task, json.dumps(meta.models), meta.provider,
                 meta.config, meta.created_at),
            )

    def finish(self, run_id: str, *, status: str, total: int | None = None,
               passed: int | None = None, failed: int | None = None,
               report_path: str | None = None, error: str | None = None) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE runs SET status=?, total=?, passed=?, failed=?, "
                "report_path=?, error=?, finished_at=? WHERE run_id=?",
                (status, total, passed, failed, report_path, error, _utcnow(), run_id),
            )

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d["models"] = json.loads(d["models"])
        return d

    def list_runs(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC, run_id DESC"
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_run(self, run_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return self._row_to_dict(row) if row else None
