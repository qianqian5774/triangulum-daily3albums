import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { parseArchiveIssue, parseTodayIssue } from "../../lib/types";
import { toRecordShopDay } from "./catalog";

function readPublicJson(path: string) {
  return JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
}

describe("Record Shop published-issue adapter", () => {
  it("maps all three current issue windows without changing record metadata", () => {
    const issue = parseTodayIssue(readPublicJson("../../../public/data/today.json"));
    const day = toRecordShopDay(issue);
    const contractPicks = issue.slots?.flatMap((slot) => slot.picks) ?? issue.picks;

    expect(day.date).toBe(issue.date);
    expect(day.runId).toBe(issue.run_id);
    expect(day.windows.map((window) => window.label)).toEqual(issue.slots?.map((slot) => slot.window_label));
    expect(day.records).toHaveLength(9);
    expect(day.records.map((record) => [record.title, record.artist, record.role])).toEqual(
      contractPicks.map((pick) => [pick.title, pick.artist_credit, pick.slot])
    );
    expect(day.records[3]?.cover).toEqual(contractPicks[3]?.cover);
    expect(day.records[3]?.releaseYear).toBe(contractPicks[3]?.first_release_year ?? null);
  });

  it("keeps a legacy archive at its published three-record shape", () => {
    const issue = parseArchiveIssue(readPublicJson("../../../public/data/archive/2026-01-19.json"));
    const day = toRecordShopDay(issue);

    expect(day.date).toBe("2026-01-19");
    expect(day.windows).toHaveLength(1);
    expect(day.records).toHaveLength(issue.picks.length);
    expect(day.records[0]).toMatchObject({
      title: issue.picks[0]?.title,
      artist: issue.picks[0]?.artist_credit,
      role: issue.picks[0]?.slot,
      cover: issue.picks[0]?.cover
    });
  });
});
