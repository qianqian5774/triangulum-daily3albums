import type { ArchiveIndex, IndexItem, TodayIssue, TodaySlot } from "./types";

export const DEFAULT_ARCHIVE_RETENTION_DAYS = 7;

function archiveSortKey(item: IndexItem) {
  return item.run_at ?? `${item.date}-${item.run_id ?? ""}`;
}

export function getRecentArchiveEntries(index: ArchiveIndex, limit = index.archive_retention_days ?? DEFAULT_ARCHIVE_RETENTION_DAYS): IndexItem[] {
  const resolvedLimit = Math.max(0, Math.floor(limit));
  const seenDates = new Set<string>();
  const sorted = [...index.items].sort((a, b) => archiveSortKey(b).localeCompare(archiveSortKey(a)));
  const entries: IndexItem[] = [];

  for (const item of sorted) {
    if (seenDates.has(item.date)) {
      continue;
    }
    seenDates.add(item.date);
    entries.push(item);
    if (entries.length >= resolvedLimit) {
      break;
    }
  }

  return entries;
}

export function getArchiveIssueSlots(issue: TodayIssue): TodaySlot[] {
  if (issue.slots?.length) {
    return [...issue.slots].sort((a, b) => a.slot_id - b.slot_id);
  }

  return [
    {
      slot_id: issue.now_slot_id ?? 0,
      window_label: "Archived selection",
      theme: issue.theme_of_day,
      picks: issue.picks
    }
  ];
}
