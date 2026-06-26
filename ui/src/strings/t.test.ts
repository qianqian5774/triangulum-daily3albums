import { describe, expect, it } from "vitest";
import { t } from "./t";

describe("localized UI copy", () => {
  it("returns English and Chinese fixed UI labels without translating metadata keys", () => {
    expect(t("nav.about", "en")).toBe("Project Info");
    expect(t("nav.about", "zh")).toBe("项目说明");
    expect(t("today.timeline.locked", "en")).toBe("Locked");
    expect(t("today.timeline.locked", "zh")).toBe("未解锁");
    expect(t("system.status.archiveMode", "en")).toBe("ARCHIVE MODE");
    expect(t("system.status.offline", "zh")).toBe("系统离线");
    expect(t("treatment.links.musicbrainz", "zh")).toBe("MusicBrainz");
    expect(t("today.intro", "en")).toBe(
      "Nine albums daily, released in three signal windows outside the usual recommendation loop."
    );
    expect(t("today.intro", "zh")).toBe("每日九张专辑，分三轮信号窗口释放，避开惯常推荐回路。");
    expect(t("treatment.slotInfo.Headliner", "en")).toContain("entry point");
    expect(t("treatment.slotInfo.DeepCut", "zh")).toContain("探索向");
    expect(t("about.body", "en")).toContain("nine album recommendations");
    expect(t("about.body", "zh")).toContain("每天发布九张专辑推荐");
  });
});
