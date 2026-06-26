import { describe, expect, it } from "vitest";
import { DEFAULT_FONT_SCALE, FONT_SCALE_TIERS, clampFontScale, stepFontScale } from "./ui-settings";

describe("UI font scale settings", () => {
  it("uses a larger default while preserving a valid A+ step", () => {
    expect(FONT_SCALE_TIERS).toEqual([1.08, 1.14, 1.2, 1.26, 1.32, 1.38, 1.44, 1.5, 1.56]);
    expect(DEFAULT_FONT_SCALE).toBe(1.38);
    expect(clampFontScale(1.7)).toBe(1.56);
  });

  it("keeps old stored scales valid and steps around the new default", () => {
    expect(clampFontScale(1.08)).toBe(1.08);
    expect(clampFontScale(0.96)).toBe(1.08);
    expect(stepFontScale(DEFAULT_FONT_SCALE, -1)).toBe(1.32);
    expect(stepFontScale(1.32, 1)).toBe(DEFAULT_FONT_SCALE);
    expect(stepFontScale(DEFAULT_FONT_SCALE, 1)).toBe(1.44);
  });
});
