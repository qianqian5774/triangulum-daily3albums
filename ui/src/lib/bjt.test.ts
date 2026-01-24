import { addDays, parseDebugTime, resolveNowState, shiftDebugTime } from "./bjt";

const seconds = (hour: number, minute: number, second: number) => hour * 3600 + minute * 60 + second;

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

  it("rejects invalid debug time", () => {
    expect(parseDebugTime("2024-03-20")).toBeNull();
  });

  it("shifts across day boundary", () => {
    const shifted = shiftDebugTime("2024-03-20T23:59:50", 20);
    expect(shifted).toBe("2024-03-21T00:00:10");
  });
});

describe("addDays", () => {
  it("adds and subtracts days on date keys", () => {
    expect(addDays("2024-03-20", 1)).toBe("2024-03-21");
    expect(addDays("2024-03-20", -1)).toBe("2024-03-19");
  });
});
