import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it } from "vitest";
import { loadArchiveDay } from "./data";
import { parseArchiveIndex, parseArchiveIssue, parseTodayIssue } from "./types";

type Mutation = { op: "set" | "delete" | "append"; path: string; value?: unknown };
type FixtureCase = {
  id: string;
  artifact_kind: "today" | "archive" | "index";
  profile: "current" | "legacy";
  base: string;
  mutations?: Mutation[];
  expected: "valid" | "invalid" | "valid_legacy";
  error_code: string | null;
};
type BundleCase = {
  id: string;
  index: string;
  index_mutations?: Mutation[];
  run_file: string | null;
  alias_file: string | null;
  expected: "valid" | "invalid";
  error_code: string | null;
};

const fixtureRoot = new URL("../../../tests/fixtures/public_contract/", import.meta.url);
const manifest = JSON.parse(readFileSync(new URL("manifest.json", fixtureRoot), "utf8")) as {
  cases: FixtureCase[];
  bundle_cases: BundleCase[];
};

const loadJson = (name: string): unknown => JSON.parse(readFileSync(new URL(name, fixtureRoot), "utf8"));
const loadBytes = (name: string): Uint8Array => new Uint8Array(readFileSync(new URL(name, fixtureRoot)));

const pointerTokens = (pointer: string) => pointer.slice(1).split("/").map((token) => token.replace(/~1/g, "/").replace(/~0/g, "~"));

function applyMutations<T>(value: T, mutations: Mutation[] = []): T {
  const result = structuredClone(value) as unknown;
  for (const mutation of mutations) {
    const parts = pointerTokens(mutation.path);
    let parent = result as Record<string, unknown> | unknown[];
    for (const token of parts.slice(0, -1)) {
      parent = (Array.isArray(parent) ? parent[Number(token)] : parent[token]) as Record<string, unknown> | unknown[];
    }
    const final = parts.at(-1) as string;
    if (mutation.op === "set") {
      if (Array.isArray(parent)) parent[Number(final)] = structuredClone(mutation.value);
      else parent[final] = structuredClone(mutation.value);
    } else if (mutation.op === "delete") {
      if (Array.isArray(parent)) parent.splice(Number(final), 1);
      else delete parent[final];
    } else {
      const target = (Array.isArray(parent) ? parent[Number(final)] : parent[final]) as unknown[];
      target.push(structuredClone(mutation.value));
    }
  }
  return result as T;
}

function invokeParser(fixture: FixtureCase, payload: unknown) {
  if (fixture.artifact_kind === "today") return parseTodayIssue(payload);
  if (fixture.artifact_kind === "archive") return parseArchiveIssue(payload);
  return parseArchiveIndex(payload);
}

describe("canonical public contract fixture matrix", () => {
  for (const fixture of manifest.cases) {
    it(fixture.id, () => {
      const payload = applyMutations(loadJson(fixture.base), fixture.mutations);
      if (fixture.expected === "valid" || fixture.expected === "valid_legacy") {
        expect(() => invokeParser(fixture, payload)).not.toThrow();
      } else {
        expect(() => invokeParser(fixture, payload)).toThrow(fixture.error_code as string);
      }
    });
  }

  it("keeps checked-in UI public examples on the current contract", () => {
    const today = JSON.parse(readFileSync(new URL("../../public/data/today.json", import.meta.url), "utf8"));
    const index = JSON.parse(readFileSync(new URL("../../public/data/index.json", import.meta.url), "utf8"));
    expect(() => parseTodayIssue(today)).not.toThrow();
    expect(() => parseArchiveIndex(index)).not.toThrow();
  });
});

const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe("archive bundle byte and identity matrix", () => {
  for (const fixture of manifest.bundle_cases) {
    it(fixture.id, async () => {
      const index = applyMutations(loadJson(fixture.index), fixture.index_mutations) as {
        items: Array<{ date: string; run_id: string }>;
      };
      const item = index.items[0];
      const runPath = `data/archive/${item.date}/${item.run_id}.json`;
      const aliasPath = `data/archive/${item.date}.json`;
      const files = new Map<string, Uint8Array>();
      if (fixture.run_file) files.set(runPath, loadBytes(fixture.run_file));
      if (fixture.alias_file) files.set(aliasPath, loadBytes(fixture.alias_file));
      globalThis.fetch = async (input) => {
        const raw = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
        const dataOffset = raw.indexOf("data/");
        const path = dataOffset >= 0 ? raw.slice(dataOffset) : raw.replace(/^\.\//, "");
        const body = files.get(path);
        return body
          ? new Response(body, { status: 200, headers: { "Content-Type": "application/json" } })
          : new Response("missing", { status: 404 });
      };

      const promise = loadArchiveDay(item.date, item.run_id);
      if (fixture.expected === "valid") {
        await expect(promise).resolves.toMatchObject({ data: { date: item.date, run_id: item.run_id } });
      } else {
        await expect(promise).rejects.toThrow(fixture.error_code as string);
      }
    });
  }
});
