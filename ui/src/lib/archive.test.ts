import { describe, expect, it } from "vitest";
import { getArchiveIssueSlots, getRecentArchiveEntries } from "./archive";
import type { ArchiveIndex, PickItem, TodayIssue } from "./types";

function pick(title: string): PickItem {
  return {
    slot: "Headliner",
    title,
    artist_credit: "Artist",
    cover: {
      has_cover: true,
      optimized_cover_url: `covers/${title}.jpg`
    }
  };
}

describe("archive helpers", () => {
  it("keeps the configured number of latest unique archive dates", () => {
    const index: ArchiveIndex = {
      output_schema_version: "1",
      archive_retention_days: 4,
      items: [
        { date: "2026-06-24", run_id: "older", run_at: "2026-06-24T06:00:00+08:00" },
        { date: "2026-06-25", run_id: "latest", run_at: "2026-06-25T06:00:00+08:00" },
        { date: "2026-06-25", run_id: "manual", run_at: "2026-06-25T12:00:00+08:00" },
        { date: "2026-06-23", run_id: "third", run_at: "2026-06-23T06:00:00+08:00" },
        { date: "2026-06-22", run_id: "fourth", run_at: "2026-06-22T06:00:00+08:00" }
      ]
    };

    expect(getRecentArchiveEntries(index).map((item) => `${item.date}:${item.run_id}`)).toEqual([
      "2026-06-25:manual",
      "2026-06-24:older",
      "2026-06-23:third",
      "2026-06-22:fourth"
    ]);
  });

  it("turns legacy single-pick archive payloads into a renderable slot", () => {
    const issue: TodayIssue = {
      output_schema_version: "1",
      date: "2026-06-25",
      run_id: "legacy",
      theme_of_day: "Signal",
      now_slot_id: 1,
      picks: [pick("legacy")]
    };

    expect(getArchiveIssueSlots(issue)).toEqual([
      {
        slot_id: 1,
        window_label: "Archived selection",
        theme: "Signal",
        picks: issue.picks
      }
    ]);
  });
});
