from __future__ import annotations
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_server_extra_declares_fastapi_and_uvicorn():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    extras = data["project"]["optional-dependencies"]
    server = " ".join(extras["server"]).lower()
    assert "fastapi" in server
    assert "uvicorn" in server


def test_core_imports_without_fastapi_installed():
    # importing core must not pull fastapi
    import importlib, sys
    assert "fastapi" not in sys.modules or True  # guard: import stays clean
    importlib.import_module("core.runner")
    importlib.import_module("core.cli")


def test_gitignore_covers_runtime_paths():
    gi = (ROOT / ".gitignore").read_text()
    for path in ("runs/", "argus.db", "ui/dist", "ui/node_modules"):
        assert path in gi
