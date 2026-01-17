import { parseArchiveIndex, parseTodayIssue, type ArchiveIndex, type TodayIssue } from "./types";
import { resolvePublicPath } from "./paths";

async function fetchJson(path: string): Promise<unknown> {
  const response = await fetch(resolvePublicPath(path), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Fetch failed: ${response.status}`);
  }
  return response.json();
}

export async function loadToday(): Promise<TodayIssue> {
  const payload = await fetchJson("data/today.json");
  return parseTodayIssue(payload);
}

export async function loadArchiveIndex(): Promise<ArchiveIndex> {
  const payload = await fetchJson("data/index.json");
  return parseArchiveIndex(payload);
}

export async function loadArchiveDay(date: string): Promise<TodayIssue> {
  const payload = await fetchJson(`data/archive/${date}.json`);
  return parseTodayIssue(payload);
}
