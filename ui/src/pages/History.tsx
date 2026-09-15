import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { RunMeta } from "../types";

export function History() {
  const [runs, setRuns] = useState<RunMeta[]>([]);
  useEffect(() => { api.listRuns().then(setRuns).catch(() => {}); }, []);
  return (
    <div className="card">
      <h2>History</h2>
      {runs.length === 0
        ? <p className="empty">No runs yet.</p>
        : <table className="rowtable">
            <thead><tr><th>run</th><th>task</th><th>models</th><th>status</th><th>pass/fail</th><th>created</th></tr></thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run_id}>
                  <td><Link to={`/runs/${r.run_id}`}>{r.run_id}</Link></td>
                  <td>{r.task}</td><td>{r.models.join(", ")}</td>
                  <td><span className={`badge badge-${r.status}`}>{r.status}</span></td>
                  <td>{r.passed ?? "—"}/{r.failed ?? "—"}</td><td>{r.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>}
    </div>
  );
}
