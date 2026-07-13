import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { parseTodayIssue } from "./types";

const fixturePath = new URL("../../../tests/fixtures/public_contract/current-issue.json", import.meta.url);

describe("today issue parsing", () => {
  it("keeps MusicBrainz rating, tags, and Wikipedia overview metadata", () => {
    const payload = JSON.parse(readFileSync(fixturePath, "utf8"));
    const metadata = {
      rating: { value: 4.35, votes_count: 23 },
      tags: [{ name: "post-hardcore", source: "musicbrainz", count: 7 }],
      wikipedia_url: "https://en.wikipedia.org/wiki/Relationship_of_Command",
      overview: {
        text: "Relationship of Command is the third studio album by American rock band At the Drive-In.",
        source: "wikipedia",
        source_url: "https://en.wikipedia.org/wiki/Relationship_of_Command",
        license_url: "https://creativecommons.org/licenses/by-sa/3.0/"
      }
    };
    payload.slots[1].picks[0].musicbrainz = metadata;
    payload.picks[0].musicbrainz = metadata;

    const issue = parseTodayIssue(payload);

    expect(issue.picks[0].musicbrainz?.rating?.value).toBe(4.35);
    expect(issue.picks[0].musicbrainz?.rating?.votes_count).toBe(23);
    expect(issue.picks[0].musicbrainz?.tags?.[0]).toEqual({
      name: "post-hardcore",
      source: "musicbrainz",
      count: 7
    });
    expect(issue.picks[0].musicbrainz?.overview?.source_url).toContain("Relationship_of_Command");
  });
});
