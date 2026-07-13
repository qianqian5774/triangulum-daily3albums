export type SlotName = "Headliner" | "Lineage" | "DeepCut";
export type ContractProfile = "current" | "legacy";

export const CURRENT_OUTPUT_SCHEMA_VERSION = "1.0";
export const LEGACY_ARCHIVE_SCHEMA_VERSIONS = new Set(["1"]);
export const CONTRACT_SLOT_IDS = [0, 1, 2] as const;
export const CONTRACT_PICK_ROLES: SlotName[] = ["Headliner", "Lineage", "DeepCut"];

export class ContractError extends Error {
  constructor(public readonly code: string, message: string) {
    super(`${code}: ${message}`);
    this.name = "ContractError";
  }
}

export interface CoverInfo {
  has_cover: boolean;
  optimized_cover_url: string;
  cover_version?: string | null;
  original_cover_url?: string | null;
}

export interface PickItem {
  slot: SlotName;
  rg_mbid?: string;
  title: string;
  artist_credit: string;
  first_release_year?: number | null;
  tags?: Array<{ name: string; source?: string; count?: number }>;
  musicbrainz?: {
    rating?: {
      value: number;
      votes_count?: number | null;
    } | null;
    tags?: Array<{ name: string; source?: string; count?: number }>;
    wikipedia_url?: string | null;
    overview?: {
      text: string;
      source?: string;
      source_url?: string | null;
      license_url?: string | null;
    } | null;
  };
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
  now_slot_id?: number | null;
  slots?: TodaySlot[];
  picks: PickItem[];
}

export interface TodaySlot {
  slot_id: number;
  window_label: string;
  theme: string;
  picks: PickItem[];
}

export interface IndexItem {
  date: string;
  run_id: string;
  theme_of_day?: string;
  slot?: number;
  run_at?: string;
}

export interface ArchiveIndex {
  output_schema_version: string;
  archive_retention_days?: number;
  items: IndexItem[];
}

const MBID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const fail = (code: string, message: string): never => {
  throw new ContractError(code, message);
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const asRecord = (value: unknown, path: string): Record<string, unknown> =>
  isRecord(value) ? value : fail("WRONG_TYPE", `${path} must be an object`);

const requiredString = (record: Record<string, unknown>, field: string, path = ""): string => {
  const label = path ? `${path}.${field}` : field;
  if (!(field in record)) fail("MISSING_REQUIRED_FIELD", `${label} is required`);
  const value = record[field];
  if (value === null) fail("NULL_REQUIRED_FIELD", `${label} cannot be null`);
  if (typeof value !== "string") fail("WRONG_TYPE", `${label} must be a string`);
  if (!value.trim()) fail("EMPTY_REQUIRED_FIELD", `${label} cannot be empty`);
  return value;
};

const optionalStringOrNull = (record: Record<string, unknown>, field: string, path: string): string | null | undefined => {
  if (!(field in record)) return undefined;
  const value = record[field];
  if (value === null) return null;
  if (typeof value !== "string") fail("WRONG_TYPE", `${path}.${field} must be a string or null`);
  return value;
};

const optionalNumberOrNull = (record: Record<string, unknown>, field: string, path: string): number | null | undefined => {
  if (!(field in record)) return undefined;
  const value = record[field];
  if (value === null) return null;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    fail("WRONG_TYPE", `${path}.${field} must be a finite number or null`);
  }
  return value;
};

const validateDate = (value: string, path: string) => {
  const parsed = new Date(`${value}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)
      || Number.isNaN(parsed.getTime())
      || parsed.toISOString().slice(0, 10) !== value) {
    fail("INVALID_DATE", `${path} must be YYYY-MM-DD`);
  }
};

const parseTags = (value: unknown, path: string): Array<{ name: string; source?: string; count?: number }> => {
  if (!Array.isArray(value)) fail("WRONG_TYPE", `${path} must be an array`);
  return value.map((raw, index) => {
    const tag = asRecord(raw, `${path}[${index}]`);
    const name = requiredString(tag, "name", `${path}[${index}]`);
    const source = optionalStringOrNull(tag, "source", `${path}[${index}]`);
    const count = optionalNumberOrNull(tag, "count", `${path}[${index}]`);
    return {
      name,
      ...(typeof source === "string" ? { source } : {}),
      ...(typeof count === "number" ? { count } : {})
    };
  });
};

const parseMusicBrainz = (value: unknown, path: string): PickItem["musicbrainz"] => {
  const musicbrainz = asRecord(value, path);
  let rating: NonNullable<PickItem["musicbrainz"]>["rating"];
  if (!("rating" in musicbrainz) || musicbrainz.rating === null) {
    rating = null;
  } else {
    const rawRating = asRecord(musicbrainz.rating, `${path}.rating`);
    const ratingValue = rawRating.value;
    if (typeof ratingValue !== "number" || !Number.isFinite(ratingValue)) {
      fail("WRONG_TYPE", `${path}.rating.value must be a finite number`);
    }
    rating = {
      value: ratingValue,
      votes_count: optionalNumberOrNull(rawRating, "votes_count", `${path}.rating`) ?? null
    };
  }

  let overview: NonNullable<PickItem["musicbrainz"]>["overview"];
  if (!("overview" in musicbrainz) || musicbrainz.overview === null) {
    overview = null;
  } else {
    const rawOverview = asRecord(musicbrainz.overview, `${path}.overview`);
    overview = {
      text: requiredString(rawOverview, "text", `${path}.overview`),
      source: optionalStringOrNull(rawOverview, "source", `${path}.overview`) ?? undefined,
      source_url: optionalStringOrNull(rawOverview, "source_url", `${path}.overview`) ?? null,
      license_url: optionalStringOrNull(rawOverview, "license_url", `${path}.overview`) ?? null
    };
  }

  return {
    rating,
    tags: !("tags" in musicbrainz) || musicbrainz.tags === null ? [] : parseTags(musicbrainz.tags, `${path}.tags`),
    wikipedia_url: optionalStringOrNull(musicbrainz, "wikipedia_url", path) ?? null,
    overview
  };
};

const parseLinks = (value: unknown, path: string): PickItem["links"] => {
  const links = asRecord(value, path);
  return {
    musicbrainz: optionalStringOrNull(links, "musicbrainz", path) ?? null,
    lastfm: optionalStringOrNull(links, "lastfm", path) ?? null,
    youtube_search: optionalStringOrNull(links, "youtube_search", path) ?? null
  };
};

const parseEvidence = (value: unknown, path: string): PickItem["evidence"] => {
  const evidence = asRecord(value, path);
  const mappingConfidence = optionalNumberOrNull(evidence, "mapping_confidence", path);
  return typeof mappingConfidence === "number" ? { mapping_confidence: mappingConfidence } : {};
};

const parseCover = (value: unknown, path: string, current: boolean): CoverInfo => {
  const cover = asRecord(value, path);
  if (current && !("has_cover" in cover)) fail("MISSING_REQUIRED_FIELD", `${path}.has_cover is required`);
  if ("has_cover" in cover && typeof cover.has_cover !== "boolean") {
    fail("WRONG_TYPE", `${path}.has_cover must be a boolean`);
  }
  return {
    has_cover: typeof cover.has_cover === "boolean" ? cover.has_cover : false,
    optimized_cover_url: requiredString(cover, "optimized_cover_url", path),
    cover_version: optionalStringOrNull(cover, "cover_version", path) ?? null,
    original_cover_url: optionalStringOrNull(cover, "original_cover_url", path) ?? null
  };
};

const parsePick = (value: unknown, path: string, profile: ContractProfile): PickItem => {
  const pick = asRecord(value, path);
  const slot = requiredString(pick, "slot", path);
  if (!CONTRACT_PICK_ROLES.includes(slot as SlotName)) {
    fail("INVALID_SLOT_ENUM", `${path}.slot=${JSON.stringify(slot)} is unsupported`);
  }
  const title = requiredString(pick, "title", path);
  const artistCredit = requiredString(pick, "artist_credit", path);
  const rawRgMbid = pick.rg_mbid;
  if (profile === "current") {
    const rgMbid = requiredString(pick, "rg_mbid", path);
    if (!MBID_RE.test(rgMbid)) fail("INVALID_RELEASE_GROUP_MBID", `${path}.rg_mbid is not a MusicBrainz UUID`);
  } else if (rawRgMbid !== undefined && rawRgMbid !== null && typeof rawRgMbid !== "string") {
    fail("WRONG_TYPE", `${path}.rg_mbid must be a string or null`);
  } else if (typeof rawRgMbid === "string" && rawRgMbid && !MBID_RE.test(rawRgMbid)) {
    fail("INVALID_RELEASE_GROUP_MBID", `${path}.rg_mbid is not a MusicBrainz UUID`);
  }
  if (profile === "legacy" && !rawRgMbid) {
    if ("album_key" in pick && pick.album_key !== null && typeof pick.album_key !== "string") {
      fail("WRONG_TYPE", `${path}.album_key must be a string or null`);
    }
    if (!(typeof pick.album_key === "string" && pick.album_key.trim()) && !(title.trim() && artistCredit.trim())) {
      fail("MISSING_STABLE_ALBUM_IDENTITY", `${path} has no stable legacy album identity`);
    }
  }

  if (!("cover" in pick)) fail("MISSING_REQUIRED_FIELD", `${path}.cover is required`);
  const firstReleaseYear = optionalNumberOrNull(pick, "first_release_year", path);
  const reason = optionalStringOrNull(pick, "reason", path);
  return {
    slot: slot as SlotName,
    ...(typeof rawRgMbid === "string" && rawRgMbid ? { rg_mbid: rawRgMbid } : {}),
    title,
    artist_credit: artistCredit,
    first_release_year: firstReleaseYear ?? null,
    tags: !("tags" in pick) || pick.tags === null ? [] : parseTags(pick.tags, `${path}.tags`),
    musicbrainz: !("musicbrainz" in pick) || pick.musicbrainz === null
      ? undefined
      : parseMusicBrainz(pick.musicbrainz, `${path}.musicbrainz`),
    cover: parseCover(pick.cover, `${path}.cover`, profile === "current"),
    links: !("links" in pick) || pick.links === null ? undefined : parseLinks(pick.links, `${path}.links`),
    evidence: !("evidence" in pick) || pick.evidence === null
      ? undefined
      : parseEvidence(pick.evidence, `${path}.evidence`),
    ...(typeof reason === "string" ? { reason } : {})
  };
};

const deepEqual = (left: unknown, right: unknown): boolean => {
  if (left === right) return true;
  if (Array.isArray(left) && Array.isArray(right)) {
    return left.length === right.length && left.every((value, index) => deepEqual(value, right[index]));
  }
  if (isRecord(left) && isRecord(right)) {
    const leftKeys = Object.keys(left).sort();
    const rightKeys = Object.keys(right).sort();
    return leftKeys.length === rightKeys.length
      && leftKeys.every((key, index) => key === rightKeys[index] && deepEqual(left[key], right[key]));
  }
  return false;
};

const parseCurrentIssue = (payload: unknown, artifactKind: "today" | "archive"): TodayIssue => {
  const issue = asRecord(payload, artifactKind);
  const version = requiredString(issue, "output_schema_version");
  if (version !== CURRENT_OUTPUT_SCHEMA_VERSION) {
    fail("UNKNOWN_SCHEMA_VERSION", `current output_schema_version=${JSON.stringify(version)} is unsupported`);
  }
  const date = requiredString(issue, "date");
  validateDate(date, "date");
  const runId = requiredString(issue, "run_id");
  const themeOfDay = requiredString(issue, "theme_of_day");
  if (!("now_slot_id" in issue)) fail("MISSING_REQUIRED_FIELD", "now_slot_id is required");
  if (!Number.isInteger(issue.now_slot_id) || !CONTRACT_SLOT_IDS.includes(issue.now_slot_id as 0 | 1 | 2)) {
    fail(typeof issue.now_slot_id === "number" ? "INVALID_SLOT_ID" : "WRONG_TYPE", "now_slot_id must be one of 0, 1, 2");
  }
  if (!Array.isArray(issue.slots)) fail("WRONG_TYPE", "slots must be an array");
  if (issue.slots.length !== 3) fail("INVALID_3X3_STRUCTURE", "slots must contain exactly 3 items");

  const slots = issue.slots.map((rawSlot, slotIndex): TodaySlot => {
    const slot = asRecord(rawSlot, `slots[${slotIndex}]`);
    if (!("slot_id" in slot)) fail("MISSING_REQUIRED_FIELD", `slots[${slotIndex}].slot_id is required`);
    if (!Number.isInteger(slot.slot_id)) fail("WRONG_TYPE", `slots[${slotIndex}].slot_id must be an integer`);
    if (!Array.isArray(slot.picks)) fail("WRONG_TYPE", `slots[${slotIndex}].picks must be an array`);
    if (slot.picks.length !== 3) fail("INVALID_3X3_STRUCTURE", `slots[${slotIndex}].picks must contain exactly 3 items`);
    const picks = slot.picks.map((pick, pickIndex) => parsePick(pick, `slots[${slotIndex}].picks[${pickIndex}]`, "current"));
    if (!picks.every((pick, pickIndex) => pick.slot === CONTRACT_PICK_ROLES[pickIndex])) {
      fail("INVALID_SLOT_COVERAGE", `slots[${slotIndex}] roles must be Headliner, Lineage, DeepCut`);
    }
    return {
      slot_id: slot.slot_id as number,
      window_label: requiredString(slot, "window_label", `slots[${slotIndex}]`),
      theme: requiredString(slot, "theme", `slots[${slotIndex}]`),
      picks
    };
  });
  if (!slots.every((slot, index) => slot.slot_id === CONTRACT_SLOT_IDS[index])) {
    fail("INVALID_SLOT_COVERAGE", "slot ids must be ordered 0, 1, 2");
  }
  if (!Array.isArray(issue.picks)) fail("WRONG_TYPE", "picks must be an array");
  if (issue.picks.length !== 3) fail("INVALID_3X3_STRUCTURE", "top-level picks must contain exactly 3 items");
  const picks = issue.picks.map((pick, index) => parsePick(pick, `picks[${index}]`, "current"));
  if (!deepEqual(issue.picks, (issue.slots[issue.now_slot_id as number] as Record<string, unknown>).picks)) {
    fail("TOP_LEVEL_PICKS_MISMATCH", "top-level picks must equal slots[now_slot_id].picks");
  }
  return {
    output_schema_version: version,
    date,
    run_id: runId,
    theme_of_day: themeOfDay,
    now_slot_id: issue.now_slot_id as number,
    slots,
    picks
  };
};

const parseLegacyArchive = (payload: unknown): TodayIssue => {
  const issue = asRecord(payload, "archive");
  const version = requiredString(issue, "output_schema_version");
  if (!LEGACY_ARCHIVE_SCHEMA_VERSIONS.has(version)) {
    fail("UNKNOWN_SCHEMA_VERSION", `legacy archive output_schema_version=${JSON.stringify(version)} is unsupported`);
  }
  const date = requiredString(issue, "date");
  validateDate(date, "date");
  const runId = requiredString(issue, "run_id");
  const themeOfDay = requiredString(issue, "theme_of_day");
  if (!Array.isArray(issue.picks)) fail("WRONG_TYPE", "legacy archive picks must be an array");
  if (!issue.picks.length) fail("INVALID_3X3_STRUCTURE", "legacy archive picks cannot be empty");
  const picks = issue.picks.map((pick, index) => parsePick(pick, `picks[${index}]`, "legacy"));
  if ("now_slot_id" in issue && issue.now_slot_id !== null && !Number.isInteger(issue.now_slot_id)) {
    fail("WRONG_TYPE", "legacy now_slot_id must be an integer or null");
  }
  return {
    output_schema_version: version,
    date,
    run_id: runId,
    theme_of_day: themeOfDay,
    now_slot_id: typeof issue.now_slot_id === "number" ? issue.now_slot_id : null,
    picks
  };
};

export function parseTodayIssue(payload: unknown): TodayIssue {
  return parseCurrentIssue(payload, "today");
}

export function parseArchiveIssue(payload: unknown): TodayIssue {
  const issue = asRecord(payload, "archive");
  const version = requiredString(issue, "output_schema_version");
  if (version === CURRENT_OUTPUT_SCHEMA_VERSION) return parseCurrentIssue(issue, "archive");
  if (LEGACY_ARCHIVE_SCHEMA_VERSIONS.has(version)) return parseLegacyArchive(issue);
  fail("UNKNOWN_SCHEMA_VERSION", `archive output_schema_version=${JSON.stringify(version)} is unsupported`);
}

export function parseArchiveIndex(payload: unknown): ArchiveIndex {
  const index = asRecord(payload, "index");
  const version = requiredString(index, "output_schema_version");
  if (version !== CURRENT_OUTPUT_SCHEMA_VERSION) {
    fail("UNKNOWN_SCHEMA_VERSION", `index output_schema_version=${JSON.stringify(version)} is unsupported`);
  }
  if (!Array.isArray(index.items)) fail("WRONG_TYPE", "index.items must be an array");
  const dates = new Set<string>();
  const identities = new Set<string>();
  const items = index.items.map((rawItem, itemIndex): IndexItem => {
    const item = asRecord(rawItem, `items[${itemIndex}]`);
    const date = requiredString(item, "date", `items[${itemIndex}]`);
    validateDate(date, `items[${itemIndex}].date`);
    const runId = requiredString(item, "run_id", `items[${itemIndex}]`);
    const identity = `${date}\u0000${runId}`;
    if (dates.has(date) || identities.has(identity)) {
      fail("DUPLICATE_ARCHIVE_IDENTITY", `duplicate/conflicting archive identity for date=${date}`);
    }
    dates.add(date);
    identities.add(identity);
    const theme = optionalStringOrNull(item, "theme_of_day", `items[${itemIndex}]`);
    const runAt = optionalStringOrNull(item, "run_at", `items[${itemIndex}]`);
    if ("slot" in item && item.slot !== null && !Number.isInteger(item.slot)) {
      fail("WRONG_TYPE", `items[${itemIndex}].slot must be an integer or null`);
    }
    return {
      date,
      run_id: runId,
      ...(typeof theme === "string" ? { theme_of_day: theme } : {}),
      ...(typeof item.slot === "number" ? { slot: item.slot } : {}),
      ...(typeof runAt === "string" ? { run_at: runAt } : {})
    };
  });
  if ("archive_retention_days" in index && index.archive_retention_days !== null) {
    if (!Number.isInteger(index.archive_retention_days)) {
      fail("WRONG_TYPE", "archive_retention_days must be an integer or null");
    }
    if ((index.archive_retention_days as number) < 1) {
      fail("INVALID_VALUE", "archive_retention_days must be >= 1");
    }
  }
  return {
    output_schema_version: version,
    archive_retention_days: typeof index.archive_retention_days === "number"
      ? index.archive_retention_days
      : undefined,
    items
  };
}
