import { describe, expect, it } from "vitest";
import { t } from "./t";

describe("localized UI copy", () => {
  it("returns English and Chinese fixed UI labels without translating metadata keys", () => {
    expect(t("nav.about", "en")).toBe("Project Info");
    expect(t("nav.about", "zh")).toBe("项目说明");
    expect(t("today.timeline.locked", "en")).toBe("Locked");
    expect(t("today.timeline.locked", "zh")).toBe("未解锁");
    expect(t("treatment.links.musicbrainz", "zh")).toBe("MusicBrainz");
    expect(t("about.body", "en")).toContain("nine album recommendations");
    expect(t("about.body", "zh")).toContain("每天发布九张专辑推荐");
  });
});
