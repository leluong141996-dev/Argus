from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.events import RunRegistry  # noqa: E402


def test_push_and_stream_until_terminal():
    reg = RunRegistry()
    ch = reg.create("r1")
    ch.push({"type": "start", "total": 2})
    ch.push({"type": "result", "done": 1, "total": 2})
    ch.push({"type": "done", "run_id": "r1", "passed": 2, "failed": 0})
    events = list(ch.stream(timeout=0.1))
    assert [e["type"] for e in events] == ["start", "result", "done"]


def test_cancel_event_toggles():
    reg = RunRegistry()
    ch = reg.create("r1")
    assert not ch.cancel_event.is_set()
    ch.cancel_event.set()
    assert ch.cancel_event.is_set()


def test_registry_get_and_remove():
    reg = RunRegistry()
    ch = reg.create("r1")
    assert reg.get("r1") is ch
    reg.remove("r1")
    assert reg.get("r1") is None
