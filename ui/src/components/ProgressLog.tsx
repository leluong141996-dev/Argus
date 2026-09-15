import type { RunEvent } from "../types";

export function ProgressLog({ events }: { events: RunEvent[] }) {
  return (
    <div className="log">
      {events.length === 0 && <div className="muted">waiting for events…</div>}
      {events.map((e, i) => {
        if (e.type === "result") {
          const ok = e.capped_by === null && e.skip_reason === null;
          return <div key={i} className={ok ? "pass" : "fail"}>
            {e.case_id} · {e.model} → {ok ? "pass" : (e.capped_by ?? "skip")}
          </div>;
        }
        if (e.type === "gate") return <div key={i}>gate: {e.status}</div>;
        if (e.type === "cancelled") return <div key={i}>cancelled at {e.done}</div>;
        if (e.type === "error") return <div key={i} className="fail">error: {e.message}</div>;
        return null;
      })}
    </div>
  );
}
