import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const todaySource = readFileSync(new URL("../routes/Today.tsx", import.meta.url), "utf8");
const dataSource = readFileSync(new URL("./use-today-data.ts", import.meta.url), "utf8");
const presentationSource = readFileSync(new URL("./use-today-presentation.ts", import.meta.url), "utf8");
const overlaySource = readFileSync(new URL("./use-today-overlay-state.ts", import.meta.url), "utf8");

describe("Today state ownership", () => {
  it("keeps data loading and recovery outside the route presentation", () => {
    expect(todaySource).toContain("useTodayData(");
    expect(todaySource).not.toContain("loadToday(");
    expect(todaySource).not.toContain("loadArchiveIndex(");
    expect(todaySource).not.toContain("window.localStorage");
    expect(dataSource).toContain("loadToday(cacheBust)");
    expect(dataSource).toContain("loadArchiveDay(entry.date, entry.run_id)");
    expect(dataSource).toContain('signalState === "SIGNAL_LOST"');
  });

  it("exposes slot and overlay actions without changing the route DOM", () => {
    expect(todaySource).toContain("useTodayPresentation(");
    expect(todaySource).toContain("useTodayOverlayState(");
    expect(todaySource).not.toContain("setFocusedId(");
    expect(todaySource).not.toContain("setShareOpen(");
    expect(todaySource).not.toContain("setAmbientActive(");
    expect(presentationSource).toContain("selectSlot");
    expect(presentationSource).toContain("returnToNow");
    expect(overlaySource).toContain("handleNext");
    expect(overlaySource).toContain("triggerLockedFeedback");
  });
});
