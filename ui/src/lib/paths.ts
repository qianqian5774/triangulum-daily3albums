export const BASE_URL = import.meta.env.BASE_URL || "./";

export function resolvePublicPath(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const normalized = path.replace(/^\.\//, "");
  return `${BASE_URL}${normalized}`;
}
