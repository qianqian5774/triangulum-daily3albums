import { getArchiveIssueSlots } from "../../lib/archive";
import type { PickItem, SlotName, TodayIssue } from "../../lib/types";

export interface RecordShopWindow {
  slotId: number;
  label: string;
  shortLabel: string;
  recordCount: number;
}

export interface RecordShopRecord {
  id: string;
  spineLabel: string;
  slotId: number;
  windowLabel: string;
  role: SlotName;
  title: string;
  artist: string;
  releaseYear: number | null;
  tags: string[];
  overview: string | null;
  selectionNote: string | null;
  rating: number | null;
  ratingVotes: number | null;
  cover: PickItem["cover"];
}

export interface RecordShopDay {
  date: string;
  runId: string;
  theme: string;
  windows: RecordShopWindow[];
  records: RecordShopRecord[];
}

function conciseWindowLabel(label: string) {
  const match = label.match(/^\d{2}:\d{2}/);
  return match?.[0] ?? label;
}

function uniqueTagNames(pick: PickItem) {
  const names = [
    ...(pick.tags ?? []).map((tag) => tag.name),
    ...(pick.musicbrainz?.tags ?? []).map((tag) => tag.name)
  ];
  return [...new Set(names.map((name) => name.trim()).filter(Boolean))];
}

function recordIdentity(issue: TodayIssue, slotId: number, pick: PickItem) {
  const pickIdentity = pick.rg_mbid ?? `${pick.title}\u0000${pick.artist_credit}`;
  return `${issue.date}\u0000${issue.run_id}\u0000${slotId}\u0000${pick.slot}\u0000${pickIdentity}`;
}

/**
 * Presentation-only adapter for the published static issue contract. It does
 * not fetch data or invent albums: every visible record is a contract pick.
 */
export function toRecordShopDay(issue: TodayIssue): RecordShopDay {
  const slots = getArchiveIssueSlots(issue);
  const windows = slots.map((slot) => ({
    slotId: slot.slot_id,
    label: slot.window_label,
    shortLabel: conciseWindowLabel(slot.window_label),
    recordCount: slot.picks.length
  }));

  const records = slots.flatMap((slot) =>
    slot.picks.map((pick) => ({
      id: recordIdentity(issue, slot.slot_id, pick),
      spineLabel: `S${slot.slot_id + 1}`,
      slotId: slot.slot_id,
      windowLabel: slot.window_label,
      role: pick.slot,
      title: pick.title,
      artist: pick.artist_credit,
      releaseYear: pick.first_release_year ?? null,
      tags: uniqueTagNames(pick),
      overview: pick.musicbrainz?.overview?.text?.trim() || null,
      selectionNote: pick.reason?.trim() || null,
      rating: pick.musicbrainz?.rating?.value ?? null,
      ratingVotes: pick.musicbrainz?.rating?.votes_count ?? null,
      cover: pick.cover
    }))
  );

  return {
    date: issue.date,
    runId: issue.run_id,
    theme: issue.theme_of_day,
    windows,
    records
  };
}
