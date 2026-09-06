import { appendCacheBuster, resolvePublicPath } from "./paths";

type StaticCoverManifest = Readonly<Record<string, string>>;

function staticCoverPath(url: string): string | null {
  const manifest = (globalThis as typeof globalThis & {
    __TRIANGULUM_STATIC_COVERS__?: StaticCoverManifest;
  }).__TRIANGULUM_STATIC_COVERS__;
  const localPath = manifest?.[url];
  return localPath?.trim() || null;
}

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
    const localPath = staticCoverPath(httpsUrl);
    const resolved = localPath ? resolvePublicPath(localPath) : httpsUrl;
    // optional: apply retry token to bust <img> error caching when user retries
    if (retryToken) {
      return addQueryParam(appendCacheBuster(resolved, cacheKey ?? undefined), "retry", retryToken.trim());
    }
    // optional: keep a lightweight cache buster based on cacheKey (cover_version)
    return appendCacheBuster(resolved, cacheKey ?? undefined);
  }
  const safe = trimmed.replace(/^\/+/, "");
  const resolved = appendCacheBuster(resolvePublicPath(safe), cacheKey ?? undefined);
  if (retryToken) {
    return addQueryParam(resolved, "retry", retryToken.trim());
  }
  return resolved;
}
