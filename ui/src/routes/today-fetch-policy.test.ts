import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./Today.tsx", import.meta.url), "utf8");

const sliceBetween = (startMarker: string, endMarker: string) => {
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker, start);
  expect(start).toBeGreaterThanOrEqual(0);
  expect(end).toBeGreaterThan(start);
  return source.slice(start, end);
};

describe("TodayRoute fetch policy", () => {
  it("keeps the today.json loader stable while the 500ms BJT clock ticks", () => {
    const storeLastGood = sliceBetween("const storeLastGood", "const loadIssue");
    const loadIssue = sliceBetween("const loadIssue", "const handleRetryNow");

    expect(storeLastGood).toContain("getBjtNowParts(loadDebugTime())");
    expect(storeLastGood).not.toContain("bjtNow.parts");
    expect(storeLastGood).toMatch(/}, \[\]\);/);

    expect(loadIssue).toContain('setSignalState((prev) => (prev !== "NORMAL" ? "RESTORED" : "NORMAL"))');
    expect(loadIssue).toMatch(/},\s*\[storeLastGood\]\s*\);/);
  });

  it("hydrates debug_time from hash router URLs into the shared debug clock path", () => {
    expect(source).toContain("readDebugTimeParam");
    expect(source).toContain("function loadDebugTimeFromLocation()");
    expect(source).toContain("readDebugTimeParam(window.location.search, window.location.hash)");
    expect(source).toContain("saveDebugTime(urlDebugTime)");
    expect(source).toContain("setBjtNow(getBjtNowParts(urlDebugTime))");
    expect(source).toContain("}, [location.hash, location.search]);");
  });
});
