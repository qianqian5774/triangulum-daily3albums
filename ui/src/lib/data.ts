import {
  ContractError,
  parseArchiveIndex,
  parseArchiveIssue,
  parseTodayIssue,
  type ArchiveIndex,
  type TodayIssue
} from "./types";
import { resolvePublicPath } from "./paths";

async function fetchJson(path: string): Promise<unknown> {
  const response = await fetch(resolvePublicPath(path), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Fetch failed: ${response.status}`);
  }
  return response.json();
}

async function fetchOptionalBytes(path: string): Promise<Uint8Array | null> {
  const response = await fetch(resolvePublicPath(path), { cache: "no-store" });
  if (response.status === 404 || response.status === 410) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Fetch failed: ${response.status}`);
  }
  return new Uint8Array(await response.arrayBuffer());
}

function bytesEqual(left: Uint8Array, right: Uint8Array): boolean {
  return left.byteLength === right.byteLength && left.every((value, index) => value === right[index]);
}

function parseJsonBytes(bytes: Uint8Array, path: string): unknown {
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch (error) {
    throw new ContractError("INVALID_JSON", `${path} is not valid UTF-8 JSON (${String(error)})`);
  }
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
    const runPath = `data/archive/${date}/${runId}.json`;
    const aliasPath = `data/archive/${date}.json`;
    const [runBytes, aliasBytes] = await Promise.all([
      fetchOptionalBytes(runPath),
      fetchOptionalBytes(aliasPath)
    ]);
    if (!runBytes && !aliasBytes) {
      throw new ContractError("ARCHIVE_MISSING", `Archive missing: date=${date} run_id=${runId}`);
    }
    if (runBytes && aliasBytes && !bytesEqual(runBytes, aliasBytes)) {
      throw new ContractError(
        "ARCHIVE_ALIAS_BYTES_MISMATCH",
        `run-specific archive and date alias differ for date=${date} run_id=${runId}`
      );
    }
    const selectedBytes = runBytes ?? aliasBytes;
    const selectedPath = runBytes ? runPath : aliasPath;
    const issue = parseArchiveIssue(parseJsonBytes(selectedBytes as Uint8Array, selectedPath));
    if (issue.date !== date || issue.run_id !== runId) {
      throw new ContractError(
        "ARCHIVE_IDENTITY_MISMATCH",
        `archive payload identity does not match date=${date} run_id=${runId}`
      );
    }
    return issue;
  }
  const aliasPath = `data/archive/${date}.json`;
  const aliasBytes = await fetchOptionalBytes(aliasPath);
  if (!aliasBytes) {
    throw new ContractError("ARCHIVE_MISSING", `Archive missing: date=${date}`);
  }
  const issue = parseArchiveIssue(parseJsonBytes(aliasBytes, aliasPath));
  if (issue.date !== date) {
    throw new ContractError("ARCHIVE_IDENTITY_MISMATCH", `archive payload date does not match date=${date}`);
  }
  return issue;
}
