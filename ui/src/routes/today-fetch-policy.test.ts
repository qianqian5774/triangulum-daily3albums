import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./Today.tsx", import.meta.url), "utf8");
const productClockSource = readFileSync(new URL("../lib/product-clock.tsx", import.meta.url), "utf8");

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
    expect(source).toContain("useProductClock()");
    expect(productClockSource).toContain("readDebugTimeParam");
    expect(productClockSource).toContain("location.search");
    expect(productClockSource).toContain("location.hash");
    expect(productClockSource).toContain("window.location.search");
    expect(productClockSource).toContain("window.location.hash");
    expect(productClockSource).toContain("applyDebugTime(formatDebugTime(parsed))");
    expect(productClockSource).toContain("location.hash, location.search");
  });
});
