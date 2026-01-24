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
  // Allow absolute URLs (e.g. Cover Art Archive). Force HTTPS to avoid mixed-content on HTTPS sites.
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    const httpsUrl = trimmed.replace(/^http:\/\//i, "https://");
    // optional: apply retry token to bust <img> error caching when user retries
    if (retryToken) {
      return addQueryParam(httpsUrl, "retry", retryToken.trim());
    }
    // optional: keep a lightweight cache buster based on cacheKey (cover_version)
    return appendCacheBuster(httpsUrl, cacheKey ?? undefined);
  }
  const safe = trimmed.replace(/^\/+/, "");
  const resolved = appendCacheBuster(resolvePublicPath(safe), cacheKey ?? undefined);
  if (retryToken) {
    return addQueryParam(resolved, "retry", retryToken.trim());
  }
  return resolved;
}
