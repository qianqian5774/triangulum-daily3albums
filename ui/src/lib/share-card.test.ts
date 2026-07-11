import { describe, expect, it } from "vitest";
import {
  getAvailableShareVersions,
  getDefaultShareVersionId,
  getShareCardAlbumCount,
  getShareCardSlots
} from "./share-card";
import type { PickItem, TodayIssue } from "./types";

function pick(title: string): PickItem {
  return {
    slot: "Headliner",
    title,
    artist_credit: "Artist",
    cover: {
      has_cover: true,
      optimized_cover_url: `https://example.com/${title}.jpg`
    }
  };
}

function riskyPick(title: string, artist: string, hasCover: boolean, optimizedCoverUrl: string): PickItem {
  return {
    slot: "Lineage",
    title,
    artist_credit: artist,
    cover: {
      has_cover: hasCover,
      optimized_cover_url: optimizedCoverUrl
    }
  };
}

const issue: TodayIssue = {
  output_schema_version: "1",
  date: "2026-06-25",
  run_id: "test-run",
  theme_of_day: "Theme",
  now_slot_id: 1,
  picks: [pick("a1"), pick("a2"), pick("a3")],
  slots: [
    {
      slot_id: 0,
      window_label: "08:00-12:29",
      theme: "Morning",
      picks: [pick("a1"), pick("a2"), pick("a3")]
    },
    {
      slot_id: 1,
      window_label: "12:30-15:59",
      theme: "Noon",
      picks: [pick("b1"), pick("b2"), pick("b3")]
    },
    {
      slot_id: 2,
      window_label: "16:00-23:59",
      theme: "Evening",
      picks: [pick("c1"), pick("c2"), pick("c3")]
    }
  ]
};

describe("share card versions", () => {
  it("only exposes versions that are unlocked by the current slot", () => {
    expect(getAvailableShareVersions(0).map((version) => version.id)).toEqual(["0800"]);
    expect(getAvailableShareVersions(1).map((version) => version.id)).toEqual(["0800", "1230"]);
    expect(getAvailableShareVersions(2).map((version) => version.id)).toEqual(["0800", "1230", "1600"]);
    expect(getAvailableShareVersions(null)).toEqual([]);
  });

  it("defaults to the fullest currently unlocked version", () => {
    expect(getDefaultShareVersionId(0)).toBe("0800");
    expect(getDefaultShareVersionId(1)).toBe("1230");
    expect(getDefaultShareVersionId(2)).toBe("1600");
  });

  it("builds the selected share card from unlocked slots only", () => {
    expect(getShareCardSlots(issue, "0800").map((slot) => slot.slotId)).toEqual([0]);
    expect(getShareCardSlots(issue, "1230").map((slot) => slot.slotId)).toEqual([0, 1]);
    expect(getShareCardSlots(issue, "1600").map((slot) => slot.slotId)).toEqual([0, 1, 2]);
    expect(getShareCardAlbumCount(issue, "1230")).toBe(6);
  });

  it("keeps risky long-title, CJK, no-cover, and broken-cover samples in stable slot groups", () => {
    const riskyIssue: TodayIssue = {
      ...issue,
      slots: [
        {
          slot_id: 0,
          window_label: "08:00-12:29",
          theme: "Long text",
          picks: [
            riskyPick(
              "A".repeat(160),
              "An Artist Name That Keeps Going Past The Normal Metadata Width ".repeat(2),
              true,
              "covers/long-title.jpg"
            ),
            riskyPick("中文标题・日本語タイトル・한국어 제목", "跨语言艺人 / アーティスト / 아티스트", true, "covers/cjk.jpg"),
            riskyPick("No Cover Signal", "Unknown Artist", false, "")
          ]
        },
        {
          slot_id: 1,
          window_label: "12:30-15:59",
          theme: "Broken cover",
          picks: [
            riskyPick("Broken remote cover", "CORS Failure Ensemble", true, "https://example.invalid/broken.jpg"),
            pick("b2"),
            pick("b3")
          ]
        },
        issue.slots![2]
      ]
    };

    const slots = getShareCardSlots(riskyIssue, "1230");

    expect(slots).toHaveLength(2);
    expect(slots.every((slot) => slot.picks.length <= 3)).toBe(true);
    expect(slots[0].picks[0].title).toHaveLength(160);
    expect(slots[0].picks[1].title).toContain("한국어");
    expect(slots[0].picks[2].cover.has_cover).toBe(false);
    expect(slots[1].picks[0].cover.optimized_cover_url).toContain("example.invalid");
  });
});
