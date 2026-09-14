"""In-process pub/sub for run progress + a cooperative cancel flag.

One RunChannel per active run_id. Producers (the run thread) push event dicts;
the SSE endpoint drains them via stream(). Stdlib only."""
from __future__ import annotations

import queue
import threading

_TERMINAL = {"done", "error", "cancelled"}


class RunChannel:
    def __init__(self) -> None:
        self._q: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self._closed = threading.Event()

    def push(self, event: dict) -> None:
        self._q.put(event)

    def close(self) -> None:
        self._closed.set()
        self._q.put(None)  # sentinel to unblock a waiting stream

    def stream(self, timeout: float = 30.0):
        """Yield queued events until a terminal event or close/sentinel."""
        while True:
            try:
                event = self._q.get(timeout=timeout)
            except queue.Empty:
                return
            if event is None:  # close sentinel
                return
            yield event
            if event.get("type") in _TERMINAL:
                return


class RunRegistry:
    def __init__(self) -> None:
        self._channels: dict[str, RunChannel] = {}
        self._lock = threading.Lock()

    def create(self, run_id: str) -> RunChannel:
        with self._lock:
            ch = RunChannel()
            self._channels[run_id] = ch
            return ch

    def get(self, run_id: str) -> RunChannel | None:
        with self._lock:
            return self._channels.get(run_id)

    def remove(self, run_id: str) -> None:
        with self._lock:
            self._channels.pop(run_id, None)
