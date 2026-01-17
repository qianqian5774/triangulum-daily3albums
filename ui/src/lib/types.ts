export type SlotName = "Headliner" | "Lineage" | "DeepCut";

export interface CoverInfo {
  has_cover: boolean;
  optimized_cover_url: string;
  original_cover_url?: string | null;
}

export interface PickItem {
  slot: SlotName;
  title: string;
  artist_credit: string;
  first_release_year?: number | null;
  tags?: Array<{ name: string; source?: string }>;
  cover: CoverInfo;
  links?: {
    musicbrainz?: string | null;
    lastfm?: string | null;
    youtube_search?: string | null;
  };
  evidence?: {
    mapping_confidence?: number;
  };
  reason?: string;
}

export interface TodayIssue {
  output_schema_version: string;
  date: string;
  run_id: string;
  theme_of_day: string;
  picks: PickItem[];
}

export interface IndexItem {
  date: string;
  run_id?: string;
  theme_of_day?: string;
}

export interface ArchiveIndex {
  output_schema_version: string;
  items: IndexItem[];
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isString = (value: unknown): value is string => typeof value === "string";

const isNumber = (value: unknown): value is number => typeof value === "number";

const isSlotName = (value: unknown): value is SlotName =>
  value === "Headliner" || value === "Lineage" || value === "DeepCut";

export function parseTodayIssue(payload: unknown): TodayIssue {
  if (!isRecord(payload)) {
    throw new Error("Invalid today payload");
  }
  const { output_schema_version, date, run_id, theme_of_day, picks } = payload;
  if (!isString(output_schema_version) || !isString(date) || !isString(run_id) || !isString(theme_of_day)) {
    throw new Error("Missing top-level today fields");
  }
  if (!Array.isArray(picks) || picks.length < 1) {
    throw new Error("Today picks missing");
  }
  const parsedPicks: PickItem[] = picks.map((pick) => {
    if (!isRecord(pick) || !isSlotName(pick.slot) || !isString(pick.title)) {
      throw new Error("Invalid pick data");
    }
    const cover = pick.cover;
    if (!isRecord(cover) || !isString(cover.optimized_cover_url)) {
      throw new Error("Invalid cover data");
    }
    return {
      slot: pick.slot,
      title: pick.title,
      artist_credit: isString(pick.artist_credit) ? pick.artist_credit : "",
      first_release_year: isNumber(pick.first_release_year) ? pick.first_release_year : null,
      tags: Array.isArray(pick.tags)
        ? pick.tags.filter(isRecord).map((tag) => ({
            name: isString(tag.name) ? tag.name : "",
            source: isString(tag.source) ? tag.source : undefined
          }))
        : [],
      cover: {
        has_cover: Boolean(cover.has_cover),
        optimized_cover_url: cover.optimized_cover_url,
        original_cover_url: isString(cover.original_cover_url) ? cover.original_cover_url : null
      },
      links: isRecord(pick.links)
        ? {
            musicbrainz: isString(pick.links.musicbrainz) ? pick.links.musicbrainz : null,
            lastfm: isString(pick.links.lastfm) ? pick.links.lastfm : null,
            youtube_search: isString(pick.links.youtube_search) ? pick.links.youtube_search : null
          }
        : undefined,
      evidence: isRecord(pick.evidence)
        ? {
            mapping_confidence: isNumber(pick.evidence.mapping_confidence)
              ? pick.evidence.mapping_confidence
              : undefined
          }
        : undefined,
      reason: isString(pick.reason) ? pick.reason : undefined
    };
  });
  return {
    output_schema_version,
    date,
    run_id,
    theme_of_day,
    picks: parsedPicks
  };
}

export function parseArchiveIndex(payload: unknown): ArchiveIndex {
  if (!isRecord(payload)) {
    throw new Error("Invalid index payload");
  }
  const { output_schema_version, items } = payload;
  if (!isString(output_schema_version) || !Array.isArray(items)) {
    throw new Error("Invalid index data");
  }
  const parsedItems = items
    .filter(isRecord)
    .map((item) => ({
      date: isString(item.date) ? item.date : "",
      run_id: isString(item.run_id) ? item.run_id : undefined,
      theme_of_day: isString(item.theme_of_day) ? item.theme_of_day : undefined
    }))
    .filter((item) => item.date);
  return {
    output_schema_version,
    items: parsedItems
  };
}
