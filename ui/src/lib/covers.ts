import { appendCacheBuster, resolvePublicPath } from "./paths";

function addQueryParam(url: string, key: string, value: string) {
  const [base, hash] = url.split("#");
  const [path, query = ""] = base.split("?");
  const params = new URLSearchParams(query);
  params.set(key, value);
  const queryString = params.toString();
  const withQuery = queryString ? `${path}?${queryString}` : path;
  return hash ? `${withQuery}#${hash}` : withQuery;
}

export function resolveCoverUrl(
  url: string | null | undefined,
  cacheKey?: string | null,
  retryToken?: string | null
) {
  if (!url) {
    return null;
  }
  const trimmed = url.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return null;
  }
  const safe = trimmed.replace(/^\/+/, "");
  const resolved = appendCacheBuster(resolvePublicPath(safe), cacheKey ?? undefined);
  if (retryToken) {
    return addQueryParam(resolved, "retry", retryToken.trim());
  }
  return resolved;
}
