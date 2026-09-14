import type { RowRecord, RunMeta } from "./types";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export interface ConfigInfo { name: string; task: string; models: string[]; provider: string; }
export interface DatasetInfo { path: string; split: string | null; }
export interface StartRunBody {
  config: string; provider_override?: string; models_override?: string[]; run_gate?: boolean;
}

export const api = {
  listConfigs: () => fetch("/api/configs").then((r) => j<ConfigInfo[]>(r)),
  listDatasets: () => fetch("/api/datasets").then((r) => j<DatasetInfo[]>(r)),
  startRun: (body: StartRunBody) =>
    fetch("/api/runs", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => j<{ run_id: string }>(r)),
  listRuns: () => fetch("/api/runs").then((r) => j<RunMeta[]>(r)),
  getRun: (id: string) =>
    fetch(`/api/runs/${id}`).then((r) => j<RunMeta & { rows: RowRecord[] }>(r)),
  cancelRun: (id: string) =>
    fetch(`/api/runs/${id}/cancel`, { method: "POST" }).then((r) => j<{ cancelling: boolean }>(r)),
};
