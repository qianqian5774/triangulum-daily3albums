import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BROWSER_DATA_TIMEOUT_MS,
  DataLoadError,
  loadArchiveDay,
  loadArchiveIndex,
  loadToday
} from "./data";
import { parseTodayIssue } from "./types";

const fixtureRoot = new URL("../../../tests/fixtures/public_contract/", import.meta.url);
const currentIssue = JSON.parse(readFileSync(new URL("current-issue.json", fixtureRoot), "utf8"));
const currentIndex = JSON.parse(readFileSync(new URL("current-index.json", fixtureRoot), "utf8"));
const encoder = new TextEncoder();
const originalFetch = globalThis.fetch;

function bytes(value: unknown, space?: number): Uint8Array {
  return encoder.encode(JSON.stringify(value, null, space));
}

function response(body: Uint8Array | string, status = 200): Response {
  return new Response(body, { status, headers: { "Content-Type": "application/json" } });
}

function requestPath(input: RequestInfo | URL): string {
  const raw = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  const offset = raw.indexOf("data/");
  return (offset >= 0 ? raw.slice(offset) : raw).split("?", 1)[0];
}

function mockFiles(files: Map<string, Uint8Array>, statuses = new Map<string, number>()) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const path = requestPath(input);
    const status = statuses.get(path);
    if (status) return response("failed", status);
    const body = files.get(path);
    return body ? response(body) : response("missing", 404);
  });
}

async function expectCode(promise: Promise<unknown>, code: DataLoadError["code"]) {
  await expect(promise).rejects.toMatchObject({ name: "DataLoadError", code });
}

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.useRealTimers();
});

describe("browser data loading semantics", () => {
  it("loads a valid Today payload without changing any fields", async () => {
    mockFiles(new Map([["data/today.json", bytes(currentIssue)]]));

    await expect(loadToday()).resolves.toEqual({ data: parseTodayIssue(currentIssue), diagnostics: [] });
  });

  it("classifies Today 404 as missing", async () => {
    mockFiles(new Map());

    await expectCode(loadToday(), "missing");
  });

  it("classifies a rejected request without retaining its sensitive URL query", async () => {
    globalThis.fetch = vi.fn(async () => {
      throw new Error("request failed for https://example.test/data/today.json?token=do-not-leak");
    });

    const error = await loadToday().catch((caught) => caught as DataLoadError);
    expect(error).toMatchObject({ code: "request_failed", details: { resource: "today" } });
    expect(JSON.stringify(error)).not.toContain("do-not-leak");
    expect(error.message).not.toContain("?");
  });

  it("classifies an HTTP failure as request_failed", async () => {
    mockFiles(new Map(), new Map([["data/today.json", 503]]));

    await expectCode(loadToday(), "request_failed");
  });

  it("classifies an aborted data request after the bounded timeout", async () => {
    vi.useFakeTimers();
    globalThis.fetch = vi.fn((_input: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      })
    );

    const pending = loadToday();
    const assertion = expectCode(pending, "timeout");
    await vi.advanceTimersByTimeAsync(BROWSER_DATA_TIMEOUT_MS);
    await assertion;
  });

  it("classifies malformed JSON as corrupt", async () => {
    mockFiles(new Map([["data/today.json", encoder.encode("{not-json")]]));

    await expectCode(loadToday(), "corrupt");
  });

  it("maps the canonical parser ContractError to invalid_schema", async () => {
    const invalid = { ...currentIssue, output_schema_version: "999" };
    mockFiles(new Map([["data/today.json", bytes(invalid)]]));

    const error = await loadToday().catch((caught) => caught as DataLoadError);
    expect(error).toMatchObject({
      code: "invalid_schema",
      details: { resource: "today", contractCode: "UNKNOWN_SCHEMA_VERSION" }
    });
  });

  it("distinguishes a legitimate empty archive index from a missing index", async () => {
    mockFiles(new Map([["data/index.json", bytes({ ...currentIndex, items: [] })]]));
    await expect(loadArchiveIndex()).resolves.toMatchObject({
      data: { items: [] },
      diagnostics: [{ code: "legitimate_empty", resource: "archive_index" }]
    });

    mockFiles(new Map());
    await expectCode(loadArchiveIndex(), "missing");
  });
});

describe("archive source and identity semantics", () => {
  const date = currentIssue.date as string;
  const runId = currentIssue.run_id as string;
  const runPath = `data/archive/${date}/${runId}.json`;
  const aliasPath = `data/archive/${date}.json`;

  it("uses the date alias as an explicit fallback when the run-specific file is missing", async () => {
    mockFiles(new Map([[aliasPath, bytes(currentIssue)]]));

    const result = await loadArchiveDay(date, runId);
    expect(result.data).toEqual(parseTodayIssue(currentIssue));
    expect(result.diagnostics).toContainEqual({
      code: "fallback_used",
      resource: "archive",
      source: "date_alias",
      reason: "run_specific_missing"
    });
    expect(result.diagnostics).toContainEqual(expect.objectContaining({
      code: "archive_source",
      selected: "date_alias",
      availability: "alias_only"
    }));
  });

  it("uses the run-specific file when the date alias is missing", async () => {
    mockFiles(new Map([[runPath, bytes(currentIssue)]]));

    await expect(loadArchiveDay(date, runId)).resolves.toMatchObject({
      data: currentIssue,
      diagnostics: [{ code: "archive_source", selected: "run_specific", availability: "run_only" }]
    });
  });

  it("accepts byte-identical run-specific and date-alias files", async () => {
    const body = bytes(currentIssue);
    mockFiles(new Map([[runPath, body], [aliasPath, body]]));

    await expect(loadArchiveDay(date, runId)).resolves.toMatchObject({
      data: currentIssue,
      diagnostics: [{ code: "archive_source", selected: "run_specific", availability: "both_identical" }]
    });
  });

  it("rejects semantically equal archive aliases when their bytes differ", async () => {
    mockFiles(new Map([[runPath, bytes(currentIssue)], [aliasPath, bytes(currentIssue, 2)]]));

    await expectCode(loadArchiveDay(date, runId), "archive_alias_mismatch");
  });

  it("classifies both missing archive paths as missing", async () => {
    mockFiles(new Map());

    await expectCode(loadArchiveDay(date, runId), "missing");
  });

  it("classifies an archive identity mismatch after canonical parsing", async () => {
    mockFiles(new Map([[runPath, bytes({ ...currentIssue, run_id: "other-run" })]]));

    await expectCode(loadArchiveDay(date, runId), "identity_mismatch");
  });

  it("classifies malformed archive bytes as corrupt", async () => {
    mockFiles(new Map([[runPath, encoder.encode("not-json")]]));

    await expectCode(loadArchiveDay(date, runId), "corrupt");
  });

  it("classifies a canonical archive contract failure as invalid_schema", async () => {
    mockFiles(new Map([[runPath, bytes({ ...currentIssue, output_schema_version: "999" })]]));

    await expectCode(loadArchiveDay(date, runId), "invalid_schema");
  });
});
