from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from server.app import create_app  # noqa: E402
from server.store import RunStore  # noqa: E402
from server.events import RunRegistry  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    cfgdir = tmp_path / "configs"; cfgdir.mkdir()
    src = Path("configs/agent_reasoning.yaml").read_text().replace("name: groq", "name: mock")
    (cfgdir / "mock_ar.yaml").write_text(src)
    monkeypatch.chdir(tmp_path)
    for name in ("datasets", "plugins", "core", "gates", "server"):
        (tmp_path / name).symlink_to(Path(__file__).resolve().parents[1] / name)
    store = RunStore(str(tmp_path / "t.db")); store.init_schema()
    return TestClient(create_app(store=store, registry=RunRegistry()))


def _parse_sse(text: str) -> list[dict]:
    return [json.loads(line[len("data: "):]) for line in text.splitlines()
            if line.startswith("data: ")]


def test_sse_streams_start_result_done(client):
    run_id = client.post("/api/runs", json={"config": "mock_ar.yaml", "run_gate": False}).json()["run_id"]
    with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        body = "".join(chunk for chunk in resp.iter_text())
    events = _parse_sse(body)
    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert "done" in types
    assert types.count("result") >= 2
