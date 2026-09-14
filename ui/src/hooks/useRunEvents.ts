import { useEffect, useState } from "react";
import type { RunEvent } from "../types";

const TERMINAL = new Set(["done", "error", "cancelled"]);

export function useRunEvents(runId: string) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [done, setDone] = useState(0);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("running");

  useEffect(() => {
    setEvents([]); setDone(0); setTotal(0); setStatus("running");
    const es = new EventSource(`/api/runs/${runId}/events`);
    es.onmessage = (m) => {
      const ev = JSON.parse(m.data) as RunEvent;
      setEvents((prev) => [...prev, ev]);
      if (ev.type === "start") setTotal(ev.total);
      if (ev.type === "result") setDone((d) => d + 1);
      if (ev.type === "cancelled") { setDone(ev.done); setStatus("cancelled"); }
      if (ev.type === "done") setStatus("done");
      if (ev.type === "error") setStatus("error");
      if (TERMINAL.has(ev.type)) es.close();
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, [runId]);

  return { events, done, total, status };
}
