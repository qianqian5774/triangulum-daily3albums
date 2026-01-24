import { parseArchiveIndex, parseTodayIssue, type ArchiveIndex, type TodayIssue } from "./types";
import { resolvePublicPath } from "./paths";

async function fetchJson(path: string): Promise<unknown> {
  const response = await fetch(resolvePublicPath(path), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Fetch failed: ${response.status}`);
  }
  return response.json();
}

export async function loadToday(cacheBust?: string): Promise<TodayIssue> {
  const suffix = cacheBust ? `?t=${cacheBust}` : "";
  const payload = await fetchJson(`data/today.json${suffix}`);
  return parseTodayIssue(payload);
}

export async function loadArchiveIndex(): Promise<ArchiveIndex> {
  const payload = await fetchJson("data/index.json");
  return parseArchiveIndex(payload);
}

export async function loadArchiveDay(date: string, runId?: string): Promise<TodayIssue> {
  if (runId) {
    try {
      const payload = await fetchJson(`data/archive/${date}/${runId}.json`);
      return parseTodayIssue(payload);
    } catch {
      // fall through
    }
  }
  const payload = await fetchJson(`data/archive/${date}.json`);
  return parseTodayIssue(payload);
}
