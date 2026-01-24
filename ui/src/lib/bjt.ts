const BJT_TIMEZONE = "Asia/Shanghai";

export type NowState = "OFFLINE" | "SLOT0" | "SLOT1" | "SLOT2";

export interface BjtParts {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
}

export interface BjtNow {
  parts: BjtParts;
  bjtDateKey: string;
  secondsSinceMidnight: number;
  nowMs: number;
  source: "debug" | "real";
}

const DEBUG_TIME_STORAGE_KEY = "tri_debug_time";

const formatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: BJT_TIMEZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false
});

const pad2 = (value: number) => value.toString().padStart(2, "0");

export const formatDateKey = (parts: Pick<BjtParts, "year" | "month" | "day">) =>
  `${parts.year}-${pad2(parts.month)}-${pad2(parts.day)}`;

export const formatBjtTime = (parts: Pick<BjtParts, "hour" | "minute" | "second">) =>
  `${pad2(parts.hour)}:${pad2(parts.minute)}:${pad2(parts.second)}`;

const getBjtPartsFromDate = (date: Date): BjtParts => {
  const parts = formatter.formatToParts(date);
  const values: Record<string, string> = {};
  for (const part of parts) {
    if (part.type !== "literal") {
      values[part.type] = part.value;
    }
  }
  return {
    year: Number(values.year),
    month: Number(values.month),
    day: Number(values.day),
    hour: Number(values.hour),
    minute: Number(values.minute),
    second: Number(values.second)
  };
};

export const bjtPartsToUtcMs = (parts: BjtParts) =>
  Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour - 8, parts.minute, parts.second);

export const parseDebugTime = (value: string): BjtParts | null => {
  const match = value.trim().match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) {
    return null;
  }
  const [, year, month, day, hour, minute, second] = match;
  const parts: BjtParts = {
    year: Number(year),
    month: Number(month),
    day: Number(day),
    hour: Number(hour),
    minute: Number(minute),
    second: Number(second ?? "0")
  };
  if (
    Number.isNaN(parts.year) ||
    Number.isNaN(parts.month) ||
    Number.isNaN(parts.day) ||
    Number.isNaN(parts.hour) ||
    Number.isNaN(parts.minute) ||
    Number.isNaN(parts.second)
  ) {
    return null;
  }
  return parts;
};

export const formatDebugTime = (parts: BjtParts) =>
  `${formatDateKey(parts)}T${formatBjtTime(parts)}`;

export const loadDebugTime = () => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(DEBUG_TIME_STORAGE_KEY);
};

export const saveDebugTime = (value: string | null) => {
  if (typeof window === "undefined") {
    return;
  }
  if (!value) {
    window.sessionStorage.removeItem(DEBUG_TIME_STORAGE_KEY);
    return;
  }
  window.sessionStorage.setItem(DEBUG_TIME_STORAGE_KEY, value);
};

export const readDebugTimeParam = (search: string) => {
  const params = new URLSearchParams(search);
  const value = params.get("debug_time");
  return value ? decodeURIComponent(value) : null;
};

export const getBjtNowParts = (debugTime: string | null): BjtNow => {
  const parsed = debugTime ? parseDebugTime(debugTime) : null;
  if (parsed) {
    const bjtDateKey = formatDateKey(parsed);
    const nowMs = bjtPartsToUtcMs(parsed);
    const secondsSinceMidnight = parsed.hour * 3600 + parsed.minute * 60 + parsed.second;
    return { parts: parsed, bjtDateKey, secondsSinceMidnight, nowMs, source: "debug" };
  }
  const now = new Date();
  const parts = getBjtPartsFromDate(now);
  const bjtDateKey = formatDateKey(parts);
  const secondsSinceMidnight = parts.hour * 3600 + parts.minute * 60 + parts.second;
  return { parts, bjtDateKey, secondsSinceMidnight, nowMs: now.getTime(), source: "real" };
};

export const resolveNowState = (secondsSinceMidnight: number): { state: NowState; slotId: number | null } => {
  if (secondsSinceMidnight < 6 * 3600) {
    return { state: "OFFLINE", slotId: null };
  }
  if (secondsSinceMidnight < 12 * 3600) {
    return { state: "SLOT0", slotId: 0 };
  }
  if (secondsSinceMidnight < 18 * 3600) {
    return { state: "SLOT1", slotId: 1 };
  }
  return { state: "SLOT2", slotId: 2 };
};

export const addDays = (dateKey: string, delta: number) => {
  const [year, month, day] = dateKey.split("-").map(Number);
  const base = new Date(Date.UTC(year, month - 1, day));
  base.setUTCDate(base.getUTCDate() + delta);
  return base.toISOString().slice(0, 10);
};

export const getNextUnlock = (now: BjtNow) => {
  const { state } = resolveNowState(now.secondsSinceMidnight);
  if (state === "OFFLINE") {
    const parts: BjtParts = { ...now.parts, hour: 6, minute: 0, second: 0 };
    return { label: "06:00", targetMs: bjtPartsToUtcMs(parts) };
  }
  if (state === "SLOT0") {
    const parts: BjtParts = { ...now.parts, hour: 12, minute: 0, second: 0 };
    return { label: "12:00", targetMs: bjtPartsToUtcMs(parts) };
  }
  if (state === "SLOT1") {
    const parts: BjtParts = { ...now.parts, hour: 18, minute: 0, second: 0 };
    return { label: "18:00", targetMs: bjtPartsToUtcMs(parts) };
  }
  const nextDateKey = addDays(now.bjtDateKey, 1);
  const [year, month, day] = nextDateKey.split("-").map(Number);
  const parts: BjtParts = { year, month, day, hour: 6, minute: 0, second: 0 };
  return { label: "06:00", targetMs: bjtPartsToUtcMs(parts) };
};

export const formatCountdown = (diffMs: number) => {
  const safe = Math.max(0, diffMs);
  const totalSeconds = Math.floor(safe / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${pad2(hours)}:${pad2(minutes)}:${pad2(seconds)}`;
};

export const shiftDebugTime = (debugTime: string, deltaSeconds: number) => {
  const parts = parseDebugTime(debugTime);
  if (!parts) {
    return null;
  }
  const nextMs = bjtPartsToUtcMs(parts) + deltaSeconds * 1000;
  const nextParts = getBjtPartsFromDate(new Date(nextMs));
  return formatDebugTime(nextParts);
};
