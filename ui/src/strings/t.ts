import { copy } from "./copy";

export function t(key: string): string {
  const parts = key.split(".");
  let current: unknown = copy;

  for (const part of parts) {
    if (typeof current !== "object" || current === null || !(part in current)) {
      return key;
    }
    current = (current as Record<string, unknown>)[part];
  }

  return typeof current === "string" ? current : key;
}
