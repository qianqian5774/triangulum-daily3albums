export const BASE_URL = import.meta.env.BASE_URL || "./";

export function resolvePublicPath(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const normalized = path.replace(/^\.\//, "").replace(/^\/+/, "");
  const base = BASE_URL.endsWith("/") ? BASE_URL : `${BASE_URL}/`;
  return `${base}${normalized}`;
}

export function appendCacheBuster(url: string, cacheKey?: string | null): string {
  if (!cacheKey) {
    return url;
  }
  const trimmed = cacheKey.trim();
  if (!trimmed) {
    return url;
  }
  const [base, hash] = url.split("#");
  const [path, query = ""] = base.split("?");
  const params = new URLSearchParams(query);
  params.set("v", trimmed);
  const queryString = params.toString();
  const withQuery = queryString ? `${path}?${queryString}` : path;
  return hash ? `${withQuery}#${hash}` : withQuery;
}
