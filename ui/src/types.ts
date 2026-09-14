export interface StageResult {
  score: number; passed: boolean; weight: number;
  tags: string[]; details: Record<string, unknown>;
}
export interface RowRecord {
  case_id: string; task: string; model: string; provider: string;
  stages: Record<string, StageResult>;
  capped_by: string | null; legacy_score: number;
  failure_tags: string[]; tokens_in: number; tokens_out: number;
  latency_ms: number; run_id: string | null; skip_reason: string | null;
}
export interface RunMeta {
  run_id: string; task: string; models: string[]; provider: string;
  config: string; status: string; total: number | null;
  passed: number | null; failed: number | null;
  report_path: string | null; error: string | null;
  created_at: string; finished_at: string | null;
}
export type RunEvent =
  | { type: "gate"; status: "pass" | "fail" }
  | { type: "start"; total: number }
  | { type: "result"; case_id: string; model: string; capped_by: string | null; legacy_score: number; skip_reason: string | null }
  | { type: "cancelled"; done: number }
  | { type: "done"; run_id: string; passed: number; failed: number }
  | { type: "error"; message: string };
