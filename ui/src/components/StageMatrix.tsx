import { aggregate, orderedStages, WEIGHTLESS } from "../lib/aggregate";
import type { RowRecord } from "../types";
import "./dashboard.css";

export function StageMatrix({ rows }: { rows: RowRecord[] }) {
  if (!rows.length) return <p>No rows.</p>;
  const groups = aggregate(rows);
  const stages = orderedStages(rows);
  return (
    <table className="matrix">
      <thead>
        <tr>
          <th>task</th><th>model</th>
          {stages.map((s) => (
            <th key={s} className={WEIGHTLESS.has(s) ? "muted" : ""}>{s}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {groups.map((g) => (
          <tr key={`${g.task}/${g.model}`}>
            <td>{g.task}</td><td>{g.model}</td>
            {stages.map((s) => {
              const a = g.stages[s];
              return (
                <td key={s} className={WEIGHTLESS.has(s) ? "muted" : ""}>
                  {a ? `${a.mean.toFixed(2)} · ${(a.passRate * 100).toFixed(0)}%` : "—"}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
