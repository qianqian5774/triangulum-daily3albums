import { getCopy, type Language } from "./copy";

export function t(key: string, language: Language = "en"): string {
  const parts = key.split(".");
  let current: unknown = getCopy(language);

  for (const part of parts) {
    if (typeof current !== "object" || current === null || !(part in current)) {
      return key;
    }
    current = (current as Record<string, unknown>)[part];
  }

  return typeof current === "string" ? current : key;
}
