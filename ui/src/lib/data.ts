import {
  ContractError,
  parseArchiveIndex,
  parseArchiveIssue,
  parseTodayIssue,
  type ArchiveIndex,
  type TodayIssue
} from "./types";
import { resolvePublicPath } from "./paths";

export const BROWSER_DATA_TIMEOUT_MS = 10_000;

export type DataLoadErrorCode =
  | "missing"
  | "request_failed"
  | "timeout"
  | "corrupt"
  | "invalid_schema"
  | "identity_mismatch"
  | "archive_alias_mismatch";

export type DataLoadResource = "today" | "archive_index" | "archive_run" | "archive_alias";

export type DataLoadDiagnostic =
  | { code: "legitimate_empty"; resource: "archive_index" }
  | {
      code: "archive_source";
      resource: "archive";
      selected: "run_specific" | "date_alias";
      availability: "run_only" | "alias_only" | "both_identical";
    }
  | {
      code: "fallback_used";
      resource: "archive";
      source: "date_alias";
      reason: "run_specific_missing";
    };

export interface DataLoadSuccess<T> {
  data: T;
  diagnostics: DataLoadDiagnostic[];
}

export class DataLoadError extends Error {
  constructor(
    public readonly code: DataLoadErrorCode,
    message: string,
    public readonly details: {
      resource: DataLoadResource;
      status?: number;
      contractCode?: string;
    }
  ) {
    super(message);
    this.name = "DataLoadError";
  }
}

function missingError(resource: DataLoadResource, status = 404, contractMessage?: string): DataLoadError {
  return new DataLoadError("missing", contractMessage ?? `Fetch failed: ${status}`, { resource, status });
}

export function normalizeDataLoadError(error: unknown, resource: DataLoadResource): DataLoadError {
  if (error instanceof DataLoadError) {
    return error;
  }
  if (error instanceof ContractError) {
    return new DataLoadError("invalid_schema", `Public contract invalid: ${error.code}`, {
      resource,
      contractCode: error.code
    });
  }
  return new DataLoadError("request_failed", "Request failed", { resource });
}

async function fetchBytes(
  path: string,
  resource: DataLoadResource,
  optional = false
): Promise<Uint8Array | null> {
  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = globalThis.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, BROWSER_DATA_TIMEOUT_MS);

  try {
    const response = await fetch(resolvePublicPath(path), {
      cache: "no-store",
      signal: controller.signal
    });
    if (response.status === 404 || response.status === 410) {
      if (optional) return null;
      throw missingError(resource, response.status);
    }
    if (!response.ok) {
      throw new DataLoadError("request_failed", `Fetch failed: ${response.status}`, {
        resource,
        status: response.status
      });
    }
    return new Uint8Array(await response.arrayBuffer());
  } catch (error) {
    if (error instanceof DataLoadError) {
      throw error;
    }
    if (timedOut) {
      throw new DataLoadError("timeout", "Request timed out", { resource });
    }
    throw new DataLoadError("request_failed", "Request failed", { resource });
  } finally {
    globalThis.clearTimeout(timeoutId);
  }
}

function bytesEqual(left: Uint8Array, right: Uint8Array): boolean {
  return left.byteLength === right.byteLength && left.every((value, index) => value === right[index]);
}

function parseJsonBytes(bytes: Uint8Array, resource: DataLoadResource): unknown {
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    throw new DataLoadError("corrupt", "INVALID_JSON: Payload is not valid UTF-8 JSON", { resource });
  }
}

function parseContract<T>(resource: DataLoadResource, parser: (payload: unknown) => T, payload: unknown): T {
  try {
    return parser(payload);
  } catch (error) {
    throw normalizeDataLoadError(error, resource);
  }
}

export async function loadToday(cacheBust?: string): Promise<DataLoadSuccess<TodayIssue>> {
  const suffix = cacheBust ? `?t=${cacheBust}` : "";
  const bytes = await fetchBytes(`data/today.json${suffix}`, "today");
  const data = parseContract("today", parseTodayIssue, parseJsonBytes(bytes as Uint8Array, "today"));
  return { data, diagnostics: [] };
}

export async function loadArchiveIndex(): Promise<DataLoadSuccess<ArchiveIndex>> {
  const bytes = await fetchBytes("data/index.json", "archive_index");
  const data = parseContract(
    "archive_index",
    parseArchiveIndex,
    parseJsonBytes(bytes as Uint8Array, "archive_index")
  );
  return {
    data,
    diagnostics: data.items.length ? [] : [{ code: "legitimate_empty", resource: "archive_index" }]
  };
}

export async function loadArchiveDay(date: string, runId?: string): Promise<DataLoadSuccess<TodayIssue>> {
  if (runId) {
    const runPath = `data/archive/${date}/${runId}.json`;
    const aliasPath = `data/archive/${date}.json`;
    const [runBytes, aliasBytes] = await Promise.all([
      fetchBytes(runPath, "archive_run", true),
      fetchBytes(aliasPath, "archive_alias", true)
    ]);
    if (!runBytes && !aliasBytes) {
      throw missingError("archive_run", 404, `ARCHIVE_MISSING: Archive missing: date=${date} run_id=${runId}`);
    }
    if (runBytes && aliasBytes && !bytesEqual(runBytes, aliasBytes)) {
      throw new DataLoadError(
        "archive_alias_mismatch",
        "ARCHIVE_ALIAS_BYTES_MISMATCH: Archive aliases differ at the byte level",
        {
          resource: "archive_run"
        }
      );
    }
    const selectedBytes = runBytes ?? aliasBytes;
    const selectedResource: DataLoadResource = runBytes ? "archive_run" : "archive_alias";
    const issue = parseContract(
      selectedResource,
      parseArchiveIssue,
      parseJsonBytes(selectedBytes as Uint8Array, selectedResource)
    );
    if (issue.date !== date || issue.run_id !== runId) {
      throw new DataLoadError(
        "identity_mismatch",
        "ARCHIVE_IDENTITY_MISMATCH: Archive payload identity does not match its index entry",
        { resource: selectedResource }
      );
    }

    const availability = runBytes && aliasBytes ? "both_identical" : runBytes ? "run_only" : "alias_only";
    const diagnostics: DataLoadDiagnostic[] = [
      {
        code: "archive_source",
        resource: "archive",
        selected: runBytes ? "run_specific" : "date_alias",
        availability
      }
    ];
    if (!runBytes) {
      diagnostics.push({
        code: "fallback_used",
        resource: "archive",
        source: "date_alias",
        reason: "run_specific_missing"
      });
    }
    return { data: issue, diagnostics };
  }

  const aliasPath = `data/archive/${date}.json`;
  const aliasBytes = await fetchBytes(aliasPath, "archive_alias", true);
  if (!aliasBytes) {
    throw missingError("archive_alias", 404, `ARCHIVE_MISSING: Archive missing: date=${date}`);
  }
  const issue = parseContract(
    "archive_alias",
    parseArchiveIssue,
    parseJsonBytes(aliasBytes, "archive_alias")
  );
  if (issue.date !== date) {
    throw new DataLoadError(
      "identity_mismatch",
      "ARCHIVE_IDENTITY_MISMATCH: Archive payload date does not match the requested date",
      { resource: "archive_alias" }
    );
  }
  return {
    data: issue,
    diagnostics: [
      {
        code: "archive_source",
        resource: "archive",
        selected: "date_alias",
        availability: "alias_only"
      }
    ]
  };
}
