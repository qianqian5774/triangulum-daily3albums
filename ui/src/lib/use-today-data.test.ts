import { describe, expect, it } from "vitest";
import { buildTodayDataDiagnostics, getTodayDateDiagnostics } from "./use-today-data";

describe("Today runtime diagnostics", () => {
  it("classifies BJT date mismatch as stale_data without changing contract parsing", () => {
    expect(getTodayDateDiagnostics("2026-07-13", "2026-07-12")).toEqual([
      {
        code: "stale_data",
        resource: "today",
        expectedDate: "2026-07-13",
        actualDate: "2026-07-12"
      }
    ]);
    expect(getTodayDateDiagnostics("2026-07-13", "2026-07-13")).toEqual([]);
  });

  it("records last-good and archive recovery as fallback_used", () => {
    expect(buildTodayDataDiagnostics({
      loadDiagnostics: [],
      archiveDiagnostics: [],
      recoverySource: "last_good",
      signalState: "SIGNAL_LOST",
      nowState: "SLOT2",
      recoveryFailed: false
    })).toContainEqual({
      code: "fallback_used",
      resource: "today_recovery",
      source: "last_good",
      reason: "current_unavailable"
    });

    expect(buildTodayDataDiagnostics({
      loadDiagnostics: [],
      archiveDiagnostics: [],
      recoverySource: "archive",
      signalState: "NORMAL",
      nowState: "OFFLINE",
      recoveryFailed: false
    })).toContainEqual({
      code: "fallback_used",
      resource: "today_recovery",
      source: "archive",
      reason: "offline_state"
    });
  });

  it("records recovery_exhausted only after every recovery source is unavailable", () => {
    expect(buildTodayDataDiagnostics({
      loadDiagnostics: [],
      archiveDiagnostics: [],
      recoverySource: null,
      signalState: "SIGNAL_LOST",
      nowState: "SLOT2",
      recoveryFailed: true
    })).toContainEqual({ code: "recovery_exhausted", resource: "today_recovery" });
  });
});
