import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const todaySource = readFileSync(new URL("./Today.tsx", import.meta.url), "utf8");
const hudSource = readFileSync(new URL("../components/Hud.tsx", import.meta.url), "utf8");
const ambientSource = readFileSync(new URL("../components/AmbientOverlay.tsx", import.meta.url), "utf8");

describe("public UI polish policies", () => {
  it("makes Enter Ambient enter standby mode without opening the album viewer", () => {
    const handlerStart = todaySource.indexOf("const handleAmbientToggle");
    const handlerEnd = todaySource.indexOf("const handleSelectSlot", handlerStart);
    expect(handlerStart).toBeGreaterThanOrEqual(0);
    expect(handlerEnd).toBeGreaterThan(handlerStart);

    const handler = todaySource.slice(handlerStart, handlerEnd);
    expect(handler).toContain("setAmbientActive(true)");
    expect(handler).not.toContain("openPick(");
    expect(handler).not.toContain("handleClose()");
    expect(todaySource).not.toContain("onClick={() => setAmbientActive((prev) => !prev)}");
  });

  it("keeps standby exit explicit through the overlay exit button", () => {
    expect(todaySource).not.toContain('window.addEventListener("keydown", exitAmbient)');
    expect(todaySource).not.toContain('window.addEventListener("click", exitAmbient)');
    expect(ambientSource).toContain("onClick={onExit}");
  });

  it("keeps the HUD fixed and measures it for content offset", () => {
    expect(hudSource).toContain("className=\"hud-shell hud-border fixed");
    expect(hudSource).toContain("--hud-height");
    expect(hudSource).toContain("ResizeObserver");
  });
});
