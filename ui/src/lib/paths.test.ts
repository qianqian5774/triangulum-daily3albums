import { describe, expect, it } from "vitest";
import { resolvePublicPath } from "./paths";

describe("resolvePublicPath", () => {
  it("resolves data paths without the legacy GitHub Pages project subpath", () => {
    const todayUrl = resolvePublicPath("data/today.json");
    const indexUrl = resolvePublicPath("/data/index.json");

    expect(todayUrl).toMatch(/data\/today\.json$/);
    expect(indexUrl).toMatch(/data\/index\.json$/);
    expect(todayUrl).not.toContain("/triangulum-daily3albums/");
    expect(indexUrl).not.toContain("/triangulum-daily3albums/");
  });

  it("keeps absolute external URLs unchanged", () => {
    expect(resolvePublicPath("https://example.com/data/today.json")).toBe(
      "https://example.com/data/today.json"
    );
  });
});
