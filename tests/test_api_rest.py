from __future__ import annotations
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from server.app import create_app  # noqa: E402
from server.store import RunStore  # noqa: E402
from server.events import RunRegistry  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    # a mock config the API can load by name
    cfgdir = tmp_path / "configs"
    cfgdir.mkdir()
    src = Path("configs/agent_reasoning.yaml").read_text().replace("name: groq", "name: mock")
    (cfgdir / "mock_ar.yaml").write_text(src)
    monkeypatch.chdir(tmp_path)
    # symlink datasets + needed dirs so relative paths resolve
    for name in ("datasets", "plugins", "core", "gates", "server"):
        (tmp_path / name).symlink_to(Path(__file__).resolve().parents[1] / name)
    store = RunStore(str(tmp_path / "t.db"))
    store.init_schema()
    app = create_app(store=store, registry=RunRegistry())
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json()["ok"] is True


def test_list_configs(client):
    names = [c["name"] for c in client.get("/api/configs").json()]
    assert "mock_ar.yaml" in names


def test_post_run_then_poll_until_done(client):
    r = client.post("/api/runs", json={"config": "mock_ar.yaml", "run_gate": False})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    for _ in range(50):
        meta = client.get(f"/api/runs/{run_id}").json()
        if meta["status"] in ("done", "error", "gate_failed", "cancelled"):
            break
        time.sleep(0.1)
    assert meta["status"] == "done"
    assert len(meta["rows"]) >= 2


def test_bad_config_returns_400(client):
    r = client.post("/api/runs", json={"config": "nope.yaml", "run_gate": False})
    assert r.status_code == 400
