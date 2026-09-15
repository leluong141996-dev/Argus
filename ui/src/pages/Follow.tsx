import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { useRunEvents } from "../hooks/useRunEvents";
import { ProgressLog } from "../components/ProgressLog";
import { StageMatrix } from "../components/StageMatrix";
import { RowTable } from "../components/RowTable";
import type { RowRecord } from "../types";

export function Follow() {
  const { id = "" } = useParams();
  const { events, done, total, status } = useRunEvents(id);
  const [rows, setRows] = useState<RowRecord[]>([]);

  useEffect(() => {
    if (status === "done" || status === "cancelled") {
      api.getRun(id).then((r) => setRows(r.rows)).catch(() => {});
    }
  }, [status, id]);

  return (
    <div>
      <div className="card">
        <h2>Run {id}</h2>
        <p className="meta">
          <span className={`badge badge-${status}`}>{status}</span>
          {" "}— {done}/{total || "?"}
        </p>
        {status === "running" &&
          <button className="btn btn-danger" onClick={() => api.cancelRun(id).catch(() => {})}>Cancel</button>}
        <h3>Progress</h3>
        <ProgressLog events={events} />
      </div>
      {rows.length > 0 && <div className="card">
        <h3>Stage matrix</h3><StageMatrix rows={rows} />
        <h3>Rows</h3><RowTable rows={rows} />
      </div>}
    </div>
  );
}
