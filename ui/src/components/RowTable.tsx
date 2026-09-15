import React, { useState } from "react";
import type { RowRecord } from "../types";
import "./dashboard.css";

function Detail({ row }: { row: RowRecord }) {
  return (
    <tr>
      <td className="detail" colSpan={6}>
        {Object.entries(row.stages).map(([name, s]) => (
          `${name}: score=${s.score} passed=${s.passed} weight=${s.weight}` +
          `${s.tags.length ? " tags=" + s.tags.join(",") : ""}` +
          `${Object.keys(s.details).length ? " details=" + JSON.stringify(s.details) : ""}\n`
        )).join("")}
      </td>
    </tr>
  );
}

export function RowTable({ rows }: { rows: RowRecord[] }) {
  const [open, setOpen] = useState<string | null>(null);
  if (!rows.length) return <p>No rows.</p>;
  return (
    <table className="rowtable">
      <thead>
        <tr><th>case</th><th>model</th><th>capped_by</th><th>score</th><th>tags</th><th>latency</th></tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const key = `${r.case_id}/${r.model}`;
          const passed = r.capped_by === null && r.skip_reason === null;
          return (
            <React.Fragment key={key}>
              <tr className="clickable" onClick={() => setOpen(open === key ? null : key)}>
                <td>{r.case_id}</td><td>{r.model}</td>
                <td className={passed ? "pass" : "fail"}>{r.capped_by ?? (r.skip_reason ? "skip" : "pass")}</td>
                <td>{r.legacy_score == null ? "—" : r.legacy_score.toFixed(2)}</td>
                <td>{r.failure_tags.join(", ")}</td>
                <td>{r.latency_ms.toFixed(1)} ms</td>
              </tr>
              {open === key && <Detail row={r} />}
            </React.Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
