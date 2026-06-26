import { describe, expect, it } from "vitest";
import { DEFAULT_FONT_SCALE, FONT_SCALE_TIERS, clampFontScale, stepFontScale } from "./ui-settings";

describe("UI font scale settings", () => {
  it("uses the new larger tier as the default and maximum", () => {
    expect(FONT_SCALE_TIERS).toEqual([0.96, 1.02, 1.08, 1.14, 1.2, 1.26, 1.32]);
    expect(DEFAULT_FONT_SCALE).toBe(1.32);
    expect(clampFontScale(1.5)).toBe(1.32);
  });

  it("keeps old stored scales valid and steps around the new default", () => {
    expect(clampFontScale(1.08)).toBe(1.08);
    expect(stepFontScale(DEFAULT_FONT_SCALE, -1)).toBe(1.26);
    expect(stepFontScale(1.26, 1)).toBe(DEFAULT_FONT_SCALE);
    expect(stepFontScale(DEFAULT_FONT_SCALE, 1)).toBe(DEFAULT_FONT_SCALE);
  });
});
