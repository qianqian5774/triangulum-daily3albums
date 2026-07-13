import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const productClockSource = readFileSync(new URL("./product-clock.tsx", import.meta.url), "utf8");
const appSource = readFileSync(new URL("../App.tsx", import.meta.url), "utf8");
const todaySource = readFileSync(new URL("../routes/Today.tsx", import.meta.url), "utf8");
const archiveSource = readFileSync(new URL("../routes/Archive.tsx", import.meta.url), "utf8");

describe("shared product clock ownership", () => {
  it("keeps exactly one 500ms ticking clock", () => {
    expect(productClockSource.match(/window\.setInterval\(tick, 500\)/g)).toHaveLength(1);
    expect(appSource).not.toContain("setInterval");
    expect(todaySource).not.toContain("setInterval");
    expect(archiveSource).not.toContain("setInterval");
  });

  it("provides the same BJT state to App, Today, and Archive", () => {
    expect(appSource).toContain("useProductClock()");
    expect(todaySource).toContain("useProductClock()");
    expect(archiveSource).toContain("useProductClock()");
    expect(appSource).toContain("<ProductClockProvider>");
  });
});
