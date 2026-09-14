"""REST + background-run wiring. FastAPI lives in the server package only."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.config import ArgusConfig, ConfigError, load_config
from core.dataset import DatasetError, split_of
from core.record_schema import RowRecord
from core.registry import UnknownTaskError
from core.report_io import read_records, write_records
from server.events import RunRegistry
from server.runs import GateAborted, RunHooks, execute_run
from server.store import RunMeta, RunStore

# NOTE: No module-level router — instantiated inside build_router to avoid
# duplicate route registration across multiple create_app() calls in tests.

CONFIG_DIR = "configs"
RUNS_DIR = "runs"


class RunRequest(BaseModel):
    config: str
    provider_override: str | None = None
    models_override: list[str] | None = None
    run_gate: bool = True


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _passed_failed(records: list[RowRecord]) -> tuple[int, int]:
    passed = sum(1 for r in records if r.pipeline.capped_by is None and r.skip_reason is None)
    return passed, len(records) - passed


def _apply_overrides(cfg: ArgusConfig, req: RunRequest) -> ArgusConfig:
    if req.provider_override:
        cfg.provider.name = req.provider_override
    if req.models_override:
        cfg.models = req.models_override
    return cfg


def start_run(store: RunStore, registry: RunRegistry, run_id: str,
              cfg: ArgusConfig, config_name: str, run_gate: bool) -> None:
    ch = registry.create(run_id)
    store.insert_running(RunMeta(
        run_id=run_id, task=cfg.task, models=cfg.models, provider=cfg.provider.name,
        config=config_name, created_at=_utcnow(),
    ))
    cfg.run_id = run_id

    def _worker() -> None:
        try:
            hooks = RunHooks(
                on_gate=lambda rep: ch.push(
                    {"type": "gate", "status": "pass" if rep.passed else "fail"}),
                on_start=lambda total: ch.push({"type": "start", "total": total}),
                on_result=lambda rec: ch.push({
                    "type": "result", "case_id": rec.case_id, "model": rec.model,
                    "capped_by": rec.pipeline.capped_by, "legacy_score": rec.legacy_score,
                    "skip_reason": rec.skip_reason,
                }),
                should_cancel=ch.cancel_event.is_set,
            )
            records = execute_run(cfg, run_gate=run_gate, hooks=hooks)
            os.makedirs(os.path.join(RUNS_DIR, run_id), exist_ok=True)
            report_path = os.path.join(RUNS_DIR, run_id, "report.json")
            write_records(records, report_path)
            passed, failed = _passed_failed(records)
            if ch.cancel_event.is_set():
                store.finish(run_id, status="cancelled", total=len(records),
                             passed=passed, failed=failed, report_path=report_path)
                ch.push({"type": "cancelled", "done": len(records)})
            else:
                store.finish(run_id, status="done", total=len(records),
                             passed=passed, failed=failed, report_path=report_path)
                ch.push({"type": "done", "run_id": run_id,
                         "passed": passed, "failed": failed})
        except GateAborted:
            store.finish(run_id, status="gate_failed", error="trust gate failed")
            ch.push({"type": "gate", "status": "fail"})
            ch.push({"type": "error", "message": "trust gate failed"})
        except Exception as e:  # noqa: BLE001
            store.finish(run_id, status="error", error=f"{type(e).__name__}: {e}")
            ch.push({"type": "error", "message": f"{type(e).__name__}: {e}"})
        finally:
            ch.close()

    threading.Thread(target=_worker, daemon=True).start()


def build_router(store: RunStore, registry: RunRegistry) -> APIRouter:
    # Correction 1: instantiate router INSIDE build_router to avoid duplicate
    # route registration when create_app() is called multiple times in tests.
    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health():
        return {"ok": True}

    @router.get("/configs")
    def configs():
        out = []
        if os.path.isdir(CONFIG_DIR):
            for name in sorted(os.listdir(CONFIG_DIR)):
                if not name.endswith((".yaml", ".yml")):
                    continue
                try:
                    cfg = load_config(os.path.join(CONFIG_DIR, name))
                    out.append({"name": name, "task": cfg.task,
                                "models": cfg.models, "provider": cfg.provider.name})
                except ConfigError:
                    continue
        return out

    @router.get("/datasets")
    def datasets():
        out = []
        for root, _dirs, files in os.walk("datasets"):
            if "cases.json" in files:
                path = os.path.join(root, "cases.json")
                # Correction 2: include case count (spec compliance)
                count = None
                try:
                    with open(path) as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        count = len(data)
                    elif isinstance(data, dict):
                        cases = data.get("cases")
                        if isinstance(cases, list):
                            count = len(cases)
                except Exception:  # noqa: BLE001
                    count = None
                out.append({"path": path, "split": split_of(path), "count": count})
        return sorted(out, key=lambda d: d["path"])

    @router.post("/runs")
    def create_run(req: RunRequest, request: Request):
        from core.runner import new_run_id
        try:
            cfg = load_config(os.path.join(CONFIG_DIR, req.config))
        except (ConfigError, DatasetError, UnknownTaskError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        cfg = _apply_overrides(cfg, req)
        run_id = new_run_id()
        start_run(store, registry, run_id, cfg, req.config, req.run_gate)
        return {"run_id": run_id}

    @router.get("/runs")
    def list_runs():
        return store.list_runs()

    @router.get("/runs/{run_id}")
    def get_run(run_id: str):
        meta = store.get_run(run_id)
        if meta is None:
            raise HTTPException(status_code=404, detail="unknown run")
        rows = []
        if meta.get("report_path") and os.path.exists(meta["report_path"]):
            rows = read_records(meta["report_path"])
        return {**meta, "rows": rows}

    @router.post("/runs/{run_id}/cancel")
    def cancel_run(run_id: str):
        ch = registry.get(run_id)
        if ch is None:
            meta = store.get_run(run_id)
            if meta is None:
                raise HTTPException(status_code=404, detail="unknown run")
            raise HTTPException(status_code=409, detail="run not active")
        ch.cancel_event.set()
        return {"cancelling": True}

    @router.get("/runs/{run_id}/events")
    def run_events(run_id: str):
        ch = registry.get(run_id)

        def gen():
            if ch is None:
                meta = store.get_run(run_id)
                if meta is None:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'unknown run'})}\n\n"
                    return
                terminal = {"type": meta["status"], "run_id": run_id,
                            "passed": meta.get("passed"), "failed": meta.get("failed")}
                yield f"data: {json.dumps(terminal)}\n\n"
                return
            for event in ch.stream():
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    return router
