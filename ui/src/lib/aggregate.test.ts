import { describe, expect, it } from "vitest";
import { aggregate, orderedStages, STAGE_ORDER } from "./aggregate";
import type { RowRecord } from "../types";

function row(model: string, retrievalPass: boolean): RowRecord {
  return {
    case_id: "c1", task: "agent_reasoning", model, provider: "mock",
    stages: {
      retrieval: { score: retrievalPass ? 1 : 0, passed: retrievalPass, weight: 1, tags: [], details: {} },
      cost: { score: 1, passed: true, weight: 0, tags: [], details: {} },
    },
    capped_by: retrievalPass ? null : "retrieval", legacy_score: retrievalPass ? 1 : 0,
    failure_tags: [], tokens_in: 1, tokens_out: 1, latency_ms: 1,
    run_id: "r", skip_reason: null,
  };
}

describe("aggregate", () => {
  it("groups by (task, model) and computes per-stage mean + pass rate", () => {
    const groups = aggregate([row("m", true), row("m", false)]);
    expect(groups).toHaveLength(1);
    const g = groups[0];
    expect(g.model).toBe("m");
    expect(g.n).toBe(2);
    expect(g.stages.retrieval.passRate).toBeCloseTo(0.5);
    expect(g.stages.retrieval.mean).toBeCloseTo(0.5);
    expect(g.stages.cost.weight).toBe(0);
  });

  it("orderedStages keeps STAGE_ORDER and drops absent stages", () => {
    const stages = orderedStages([row("m", true)]);
    expect(stages).toEqual(["retrieval", "cost"]);
    expect(STAGE_ORDER[0]).toBe("retrieval");
  });
});
