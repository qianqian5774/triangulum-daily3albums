import { afterEach, describe, it, expect, vi } from "vitest";
import { resolveCoverUrl } from "./covers";

afterEach(() => vi.unstubAllGlobals());

describe("resolveCoverUrl", () => {
  it("returns null for empty", () => {
    expect(resolveCoverUrl(null)).toBeNull();
    expect(resolveCoverUrl(undefined)).toBeNull();
    expect(resolveCoverUrl("")).toBeNull();
    expect(resolveCoverUrl("   ")).toBeNull();
  });

  it("forces https for http absolute url", () => {
    const out = resolveCoverUrl("http://coverartarchive.org/a.jpg", "k1");
    expect(out).toMatch(/^https:\/\//);
  });

  it("keeps https for https absolute url", () => {
    const out = resolveCoverUrl("https://coverartarchive.org/a.jpg", "k2");
    expect(out).toMatch(/^https:\/\//);
  });

  it("adds cache buster v=cacheKey when provided", () => {
    const out = resolveCoverUrl("https://coverartarchive.org/a.jpg", "cache123");
    expect(out).toContain("v=cache123");
  });

  it("adds retry token when provided", () => {
    const out = resolveCoverUrl("https://coverartarchive.org/a.jpg", "k3", "retry1");
    expect(out).toContain("retry=retry1");
  });

  it("resolves relative public path and strips leading slash", () => {
    const out = resolveCoverUrl("/assets/covers/a.webp", "k4");
    // 不硬编码 BASE_URL，只要求路径片段存在 + cacheKey 生效
    expect(out).toContain("assets/covers/a.webp");
    expect(out).toContain("v=k4");
  });

  it("preserves existing query and appends v=", () => {
    const out = resolveCoverUrl("assets/covers/a.webp?x=1", "k5");
    expect(out).toContain("x=1");
    expect(out).toContain("v=k5");
  });

  it("prefers the deployment-local asset mapped from a remote cover URL", () => {
    vi.stubGlobal("__TRIANGULUM_STATIC_COVERS__", {
      "https://coverartarchive.org/a.jpg": "assets/covers/aabbcc.jpg"
    });

    const out = resolveCoverUrl("http://coverartarchive.org/a.jpg", "cover-version");

    expect(out).toContain("assets/covers/aabbcc.jpg");
    expect(out).toContain("v=cover-version");
    expect(out).not.toContain("coverartarchive.org");
  });
});
