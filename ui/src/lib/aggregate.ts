import type { RowRecord } from "../types";

export const STAGE_ORDER = [
  "retrieval", "reasoning", "action_selection", "safety", "cost", "latency",
];
export const WEIGHTLESS = new Set(["cost", "latency"]);

export interface StageAgg { mean: number; passRate: number; n: number; weight: number; }
export interface GroupSummary {
  task: string; model: string; n: number; stages: Record<string, StageAgg>;
}

/** Stages present in the given rows, STAGE_ORDER-known first, then unknown stages sorted. */
export function orderedStages(rows: RowRecord[]): string[] {
  const present = new Set<string>();
  for (const r of rows) {
    for (const k of Object.keys(r.stages)) present.add(k);
  }
  const known = STAGE_ORDER.filter((s) => present.has(s));
  const unknown = [...present].filter((s) => !STAGE_ORDER.includes(s)).sort();
  return [...known, ...unknown];
}

/**
 * Groups rows by (task, model) and computes per-stage mean score, pass rate, n, and weight.
 * Mirrors the reference semantics in dashboards/web/template.html:
 * - Group key uses "|" separator (safe against spaces in task/model names).
 * - task and model are stored directly on the group, no split needed.
 * - Weight is taken from the last row that has the stage (last-wins, mirrors reference).
 * - Unknown stages (not in STAGE_ORDER) are included after known ones, sorted.
 */
export function aggregate(rows: RowRecord[]): GroupSummary[] {
  const groups = new Map<string, { task: string; model: string; rows: RowRecord[] }>();
  for (const r of rows) {
    const key = `${r.task}|${r.model}`;
    if (!groups.has(key)) groups.set(key, { task: r.task, model: r.model, rows: [] });
    groups.get(key)!.rows.push(r);
  }

  const out: GroupSummary[] = [];
  for (const { task, model, rows: groupRows } of groups.values()) {
    // Accumulate per-stage sums
    const acc: Record<string, { sum: number; pass: number; n: number; weight: number }> = {};
    for (const r of groupRows) {
      for (const [name, st] of Object.entries(r.stages)) {
        if (!acc[name]) acc[name] = { sum: 0, pass: 0, n: 0, weight: st.weight };
        acc[name].sum += st.score;
        acc[name].pass += st.passed ? 1 : 0;
        acc[name].n += 1;
        acc[name].weight = st.weight; // last-wins (matches reference)
      }
    }

    const stages: Record<string, StageAgg> = {};
    for (const [name, s] of Object.entries(acc)) {
      stages[name] = {
        mean: s.n ? s.sum / s.n : 0,
        passRate: s.n ? s.pass / s.n : 0,
        n: s.n,
        weight: s.weight,
      };
    }

    out.push({ task, model, n: groupRows.length, stages });
  }

  out.sort((a, b) => (a.task + a.model).localeCompare(b.task + b.model));
  return out;
}
