import { describe, expect, it } from "vitest";
import { parseTodayIssue } from "./types";

describe("today issue parsing", () => {
  it("keeps MusicBrainz rating, tags, and Wikipedia overview metadata", () => {
    const issue = parseTodayIssue({
      output_schema_version: "1",
      date: "2026-06-26",
      run_id: "run",
      theme_of_day: "post-hardcore",
      picks: [
        {
          slot: "Headliner",
          title: "Relationship of Command",
          artist_credit: "At the Drive-In",
          first_release_year: 2000,
          tags: [{ name: "post-hardcore", source: "lastfm" }],
          musicbrainz: {
            rating: { value: 4.35, votes_count: 23 },
            tags: [{ name: "post-hardcore", source: "musicbrainz", count: 7 }],
            wikipedia_url: "https://en.wikipedia.org/wiki/Relationship_of_Command",
            overview: {
              text: "Relationship of Command is the third studio album by American rock band At the Drive-In.",
              source: "wikipedia",
              source_url: "https://en.wikipedia.org/wiki/Relationship_of_Command",
              license_url: "https://creativecommons.org/licenses/by-sa/3.0/"
            }
          },
          cover: {
            has_cover: true,
            optimized_cover_url: "cover.jpg"
          }
        }
      ]
    });

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
