"""FastAPI app factory. Mounts the API router and (if built) the SPA."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server.api import build_router
from server.events import RunRegistry
from server.store import RunStore, default_db_path

UI_DIST = "ui/dist"


def create_app(store: RunStore | None = None,
               registry: RunRegistry | None = None) -> FastAPI:
    store = store or RunStore(default_db_path())
    store.init_schema()
    registry = registry or RunRegistry()

    app = FastAPI(title="ARGUS")
    app.include_router(build_router(store, registry))

    if os.path.isdir(UI_DIST):
        app.mount("/", StaticFiles(directory=UI_DIST, html=True), name="spa")

    return app
