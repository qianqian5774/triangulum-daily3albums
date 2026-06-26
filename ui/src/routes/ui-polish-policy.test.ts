import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const todaySource = readFileSync(new URL("./Today.tsx", import.meta.url), "utf8");
const hudSource = readFileSync(new URL("../components/Hud.tsx", import.meta.url), "utf8");
const ambientSource = readFileSync(new URL("../components/AmbientOverlay.tsx", import.meta.url), "utf8");
const stylesSource = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

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

  it("keeps manual Ambient entry scoped to Time Lab and doubles the idle delay", () => {
    expect(todaySource).toContain("const AMBIENT_IDLE_DELAY_MS = 120000");
    const normalTodayStart = todaySource.indexOf('${ambientActive ? "ambient-mode" : ""}');
    expect(normalTodayStart).toBeGreaterThanOrEqual(0);
    const toolbarStart = todaySource.indexOf(
      '<div className="ambient-fade flex flex-wrap items-center gap-3">',
      normalTodayStart
    );
    const toolbarEnd = todaySource.indexOf("{debugPanel}", toolbarStart);
    expect(toolbarStart).toBeGreaterThanOrEqual(0);
    expect(toolbarEnd).toBeGreaterThan(toolbarStart);
    const toolbar = todaySource.slice(toolbarStart, toolbarEnd);
    expect(toolbar).not.toContain("today.ambientEnter");
    expect(toolbar).not.toContain("today.archiveCta");

    const debugPanelStart = todaySource.indexOf("const debugPanel = debugPanelEnabled");
    const debugPanelEnd = todaySource.indexOf("if (nowState === \"OFFLINE\")", debugPanelStart);
    expect(debugPanelStart).toBeGreaterThanOrEqual(0);
    expect(debugPanelEnd).toBeGreaterThan(debugPanelStart);
    const debugPanel = todaySource.slice(debugPanelStart, debugPanelEnd);
    expect(debugPanel).toContain("today.ambientEnter");
    expect(debugPanel).toContain("data-testid=\"ambient-toggle\"");
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

  it("shows all unlocked albums in the HUD marquee and removes old timeline art", () => {
    expect(todaySource).toContain(".filter((slot) => slot.slot_id <= nowSlotId)");
    expect(todaySource).toContain(".flatMap((slot) => slot.picks)");
    expect(stylesSource).toContain("animation: marquee 18s linear infinite");
    const timelineArtStart = stylesSource.indexOf(".today-layout > aside::before");
    const timelineArtEnd = stylesSource.indexOf(".today-layout > aside > *", timelineArtStart);
    expect(timelineArtStart).toBeGreaterThanOrEqual(0);
    expect(timelineArtEnd).toBeGreaterThan(timelineArtStart);
    const timelineArt = stylesSource.slice(timelineArtStart, timelineArtEnd);
    expect(timelineArt).toContain("content: none");
    expect(timelineArt).not.toContain("background-image");
  });
});
