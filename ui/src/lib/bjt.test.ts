// ui/src/lib/bjt.test.ts
import { describe, it, expect } from "vitest";
import productSchedule from "../../../tests/fixtures/product_schedule.json";
import {
  addDays,
  BJT_TIMEZONE,
  getBjtNowParts,
  getNextUnlock,
  parseDebugTime,
  PRODUCT_SCHEDULE,
  readDebugFlagParam,
  readDebugTimeParam,
  resolveNowState,
  resolveVisualTheme,
  shiftDebugTime
} from "./bjt";

const seconds = (hour: number, minute: number, second: number) =>
  hour * 3600 + minute * 60 + second;

describe("resolveNowState", () => {
  it("uses the canonical product timezone", () => {
    expect(BJT_TIMEZONE).toBe(productSchedule.timezone);
  });

  it("matches the canonical schedule boundary fixture", () => {
    for (const boundary of productSchedule.boundary_cases) {
      const [hour, minute, second] = boundary.time.split(":").map(Number);
      expect(resolveNowState(seconds(hour, minute, second))).toEqual({
        state: boundary.ui_state,
        slotId: boundary.ui_slot_id
      });
    }
  });

  it("keeps the UI schedule aligned with canonical slot metadata", () => {
    expect(PRODUCT_SCHEDULE).toHaveLength(productSchedule.slots_per_day);
    expect(PRODUCT_SCHEDULE.map((slot) => ({
      slotId: slot.slotId,
      start: `${slot.label}:00`,
      windowLabel: slot.windowLabel
    }))).toEqual(productSchedule.slots.map((slot) => ({
      slotId: slot.slot_id,
      start: slot.start,
      windowLabel: slot.ui_window_label
    })));
  });
});

describe("resolveVisualTheme", () => {
  it("switches to night exactly at 20:00 BJT and back to day at 08:00 BJT", () => {
    expect(resolveVisualTheme(seconds(19, 59, 59))).toBe("day");
    expect(resolveVisualTheme(seconds(20, 0, 0))).toBe("night");
    expect(resolveVisualTheme(seconds(7, 59, 59))).toBe("night");
    expect(resolveVisualTheme(seconds(8, 0, 0))).toBe("day");
  });

  it("is driven by debug_time through the normal BJT clock path", () => {
    const dayNow = getBjtNowParts("2026-06-13T19:59:58");
    const nightNow = getBjtNowParts("2026-06-13T20:00:00");

    expect(dayNow.source).toBe("debug");
    expect(nightNow.source).toBe("debug");
    expect(resolveVisualTheme(dayNow.secondsSinceMidnight)).toBe("day");
    expect(resolveVisualTheme(nightNow.secondsSinceMidnight)).toBe("night");
  });
});

describe("getNextUnlock", () => {
  it("uses the 08:00, 12:30, and 16:00 product boundaries", () => {
    expect(getNextUnlock(getBjtNowParts("2026-07-11T07:59:59")).label).toBe("08:00");
    expect(getNextUnlock(getBjtNowParts("2026-07-11T08:00:00")).label).toBe("12:30");
    expect(getNextUnlock(getBjtNowParts("2026-07-11T12:30:00")).label).toBe("16:00");
    expect(getNextUnlock(getBjtNowParts("2026-07-11T16:00:00")).label).toBe("08:00");
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
    expect(readDebugTimeParam("?debug_time=2024-03-20T08:00:00", "")).toBe("2024-03-20T08:00:00");
    expect(readDebugTimeParam("", "?debug_time=2024-03-20T08:00:00")).toBe("2024-03-20T08:00:00");
  });

  it("reads debug_time and debug flag from hash router URLs", () => {
    expect(readDebugTimeParam("#/archive?debug_time=2024-03-20T12:30:00")).toBe("2024-03-20T12:30:00");
    expect(readDebugFlagParam("#/?debug=1")).toBe(true);
    expect(readDebugFlagParam("?debug=true")).toBe(true);
    expect(readDebugFlagParam("#/?debug=0")).toBe(false);
  });

  it("drives frontend slot state from simulated BJT debug times", () => {
    const cases = [
      ["2024-03-20T07:59:00", "OFFLINE", null],
      ["2024-03-20T08:00:00", "SLOT0", 0],
      ["2024-03-20T12:30:00", "SLOT1", 1],
      ["2024-03-20T16:00:00", "SLOT2", 2]
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
