// ui/src/lib/bjt.test.ts
import { describe, it, expect } from "vitest";
import { addDays, getBjtNowParts, parseDebugTime, readDebugTimeParam, resolveNowState, shiftDebugTime } from "./bjt";

const seconds = (hour: number, minute: number, second: number) =>
  hour * 3600 + minute * 60 + second;

describe("resolveNowState", () => {
  it("handles boundaries with left-closed/right-open windows", () => {
    expect(resolveNowState(seconds(5, 59, 59)).state).toBe("OFFLINE");
    expect(resolveNowState(seconds(6, 0, 0)).state).toBe("SLOT0");
    expect(resolveNowState(seconds(11, 59, 59)).state).toBe("SLOT0");
    expect(resolveNowState(seconds(12, 0, 0)).state).toBe("SLOT1");
    expect(resolveNowState(seconds(17, 59, 59)).state).toBe("SLOT1");
    expect(resolveNowState(seconds(18, 0, 0)).state).toBe("SLOT2");
    expect(resolveNowState(seconds(23, 59, 59)).state).toBe("SLOT2");
    expect(resolveNowState(seconds(0, 0, 0)).state).toBe("OFFLINE");
  });
});

describe("debug time parsing", () => {
  it("parses valid debug time", () => {
    const parts = parseDebugTime("2024-03-20T05:59:50");
    expect(parts).not.toBeNull();
    expect(parts?.hour).toBe(5);
  });

  it("parses debug time without seconds", () => {
    const parts = parseDebugTime("2024-03-20T05:59");
    expect(parts?.second).toBe(0);
  });

  it("rejects invalid debug time", () => {
    expect(parseDebugTime("2024-03-20")).toBeNull();
  });

  it("shifts across day boundary", () => {
    const shifted = shiftDebugTime("2024-03-20T23:59:50", 20);
    expect(shifted).toBe("2024-03-21T00:00:10");
  });

  it("reads URL encoded debug_time", () => {
    const value = readDebugTimeParam("?debug_time=2024-03-20T05%3A59%3A50");
    expect(value).toBe("2024-03-20T05:59:50");
  });

  it("reads debug_time from router search or window search", () => {
    expect(readDebugTimeParam("?debug_time=2024-03-20T06:00:00", "")).toBe("2024-03-20T06:00:00");
    expect(readDebugTimeParam("", "?debug_time=2024-03-20T06:00:00")).toBe("2024-03-20T06:00:00");
  });

  it("drives frontend slot state from simulated BJT debug times", () => {
    const cases = [
      ["2024-03-20T05:59:00", "OFFLINE", null],
      ["2024-03-20T06:00:00", "SLOT0", 0],
      ["2024-03-20T12:00:00", "SLOT1", 1],
      ["2024-03-20T18:00:00", "SLOT2", 2]
    ] as const;

    for (const [debugTime, state, slotId] of cases) {
      const now = getBjtNowParts(debugTime);
      expect(resolveNowState(now.secondsSinceMidnight)).toEqual({ state, slotId });
    }
  });
});

describe("addDays", () => {
  it("adds and subtracts days on date keys", () => {
    expect(addDays("2024-03-20", 1)).toBe("2024-03-21");
    expect(addDays("2024-03-20", -1)).toBe("2024-03-19");
  });
});
