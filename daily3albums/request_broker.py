from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse, urlsplit, parse_qsl, urlencode, urlunsplit

import httpx


def _parse_ttl(s: str) -> int:
    s = s.strip().lower()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    n = int(s[:-1])
    u = s[-1]
    if u not in units:
        raise ValueError(f"Bad TTL format: {s}")
    return n * units[u]


def _now_epoch() -> int:
    return int(time.time())


def _redact_url(url: str) -> str:
    # 避免把 api_key/token 打进日志/截图
    sensitive = {
        "api_key", "api_sig", "token", "access_token",
        "key", "secret", "signature", "session_key"
    }
    try:
        parts = urlsplit(url)
        q = []
        for k, v in parse_qsl(parts.query, keep_blank_values=True):
            if k.lower() in sensitive:
                q.append((k, "***"))
            else:
                q.append((k, v))
        new_query = urlencode(q, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))
    except Exception:
        return url


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_delay_ms: int = 400
    max_delay_ms: int = 6000
    jitter: bool = True


@dataclass
class HostPolicy:
    rate_limit_rps: float = 1.0
    ttl_default_s: int = 86400
    negative_cache_ttl_s: int = 3600
    retry: RetryPolicy = field(default_factory=RetryPolicy)


class RequestBroker:
    def __init__(
        self,
        repo_root: Path,
        endpoint_policies: dict,
        logger: Optional[Callable[[str], None]] = None,
        timeout_s: float = 20.0,
    ) -> None:
        self.repo_root = repo_root
        self.policies_raw = endpoint_policies or {}
        self.logger = logger
        self.timeout_s = float(timeout_s)

        self.state_dir = repo_root / ".state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.state_dir / "cache.sqlite"
        self.conn = sqlite3.connect(self.db_path.as_posix(), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS http_cache (
              key TEXT PRIMARY KEY,
              url TEXT NOT NULL,
              status INTEGER NOT NULL,
              headers_json TEXT NOT NULL,
              body BLOB NOT NULL,
              created_at INTEGER NOT NULL,
              expires_at INTEGER NOT NULL
            )
            """
        )
        self.conn.commit()

        self._host_last_ts: dict[str, float] = {}

        self.client = httpx.Client(
            timeout=httpx.Timeout(self.timeout_s),
            follow_redirects=True,
        )

    def close(self) -> None:
        try:
            self.client.close()
        finally:
            self.conn.close()

    def _log(self, msg: str) -> None:
        if self.logger:
            self.logger(msg)

    def _host_policy(self, host: str) -> HostPolicy:
        hosts = (self.policies_raw or {}).get("hosts", {})
        h = hosts.get(host, {}) if isinstance(hosts, dict) else {}

        retry_raw = h.get("retry", {}) if isinstance(h, dict) else {}
        rp = RetryPolicy(
            max_attempts=int(retry_raw.get("max_attempts", 4)),
            base_delay_ms=int(retry_raw.get("base_delay_ms", 400)),
            max_delay_ms=int(retry_raw.get("max_delay_ms", 6000)),
            jitter=bool(retry_raw.get("jitter", True)),
        )

        ttl_default = h.get("ttl_default", "1d")
        neg_ttl = h.get("negative_cache_ttl", "1h")

        return HostPolicy(
            rate_limit_rps=float(h.get("rate_limit_rps", 1.0)),
            ttl_default_s=_parse_ttl(ttl_default),
            negative_cache_ttl_s=_parse_ttl(neg_ttl),
            retry=rp,
        )

    def _rate_limit(self, host: str) -> None:
        pol = self._host_policy(host)
        rps = max(pol.rate_limit_rps, 0.01)
        min_interval = 1.0 / rps

        now = time.monotonic()
        last = self._host_last_ts.get(host, 0.0)
        wait = (last + min_interval) - now
        if wait > 0:
            self._log(f"RATE_LIMIT host={host} sleep={wait:.3f}s")
            time.sleep(wait)
        self._host_last_ts[host] = time.monotonic()

    def _cache_key(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _cache_get(self, key: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT url,status,headers_json,body,created_at,expires_at FROM http_cache WHERE key=?",
            (key,),
        ).fetchone()
        if not row:
            return None

        url, status, headers_json, body, created_at, expires_at = row
        if _now_epoch() >= int(expires_at):
            self.conn.execute("DELETE FROM http_cache WHERE key=?", (key,))
            self.conn.commit()
            return None

        return {
            "url": url,
            "status": int(status),
            "headers": json.loads(headers_json),
            "body": body,
            "created_at": int(created_at),
            "expires_at": int(expires_at),
        }

    def _cache_put(self, key: str, url: str, status: int, headers: dict, body: bytes, ttl_s: int) -> None:
        created = _now_epoch()
        expires = created + max(int(ttl_s), 1)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO http_cache(key,url,status,headers_json,body,created_at,expires_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (key, url, int(status), json.dumps(headers, ensure_ascii=False), body, created, expires),
        )
        self.conn.commit()

    def get(self, url: str, headers: Optional[dict] = None, ttl_override_s: Optional[int] = None) -> bytes:
        parsed = urlparse(url)
        host = parsed.netloc

        key = self._cache_key(url)
        cached = self._cache_get(key)
        if cached:
            status = int(cached.get("status", 0))
            if 200 <= status <= 299:
                self._log(f"CACHE HIT url={_redact_url(url)}")
                return cached["body"]

            # 负缓存（非 2xx）保持与首次请求一致：直接抛异常
            self._log(f"CACHE HIT NEG status={status} url={_redact_url(url)}")
            raise RuntimeError(f"HTTP {status} for {_redact_url(url)} (cached)")

        self._log(f"CACHE MISS url={_redact_url(url)}")

        pol = self._host_policy(host)
        ttl_ok = int(ttl_override_s) if ttl_override_s is not None else pol.ttl_default_s

        attempt = 0
        while True:
            attempt += 1
            self._rate_limit(host)

            try:
                resp = self.client.get(url, headers=headers)
                status = int(resp.status_code)

                if status == 429 or 500 <= status <= 599:
                    if attempt < pol.retry.max_attempts:
                        delay = min(pol.retry.max_delay_ms, pol.retry.base_delay_ms * (2 ** (attempt - 1)))
                        if pol.retry.jitter:
                            delay = int(delay * (0.6 + 0.8 * random.random()))
                        self._log(f"RETRY status={status} attempt={attempt} delay_ms={delay} url={_redact_url(url)}")
                        time.sleep(delay / 1000.0)
                        continue

                body = resp.content
                hdrs = dict(resp.headers)

                if 200 <= status <= 299:
                    self._cache_put(key, url, status, hdrs, body, ttl_ok)
                    return body

                self._cache_put(key, url, status, hdrs, body, pol.negative_cache_ttl_s)
                raise RuntimeError(f"HTTP {status} for {_redact_url(url)}")

            except (httpx.TimeoutException, httpx.TransportError) as e:
                if attempt < pol.retry.max_attempts:
                    delay = min(pol.retry.max_delay_ms, pol.retry.base_delay_ms * (2 ** (attempt - 1)))
                    if pol.retry.jitter:
                        delay = int(delay * (0.6 + 0.8 * random.random()))
                    self._log(f"RETRY error={type(e).__name__} attempt={attempt} delay_ms={delay} url={_redact_url(url)}")
                    time.sleep(delay / 1000.0)
                    continue
                raise

    def get_json(self, url: str, headers: Optional[dict] = None, ttl_override_s: Optional[int] = None) -> Any:
        raw = self.get(url, headers=headers, ttl_override_s=ttl_override_s)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Bad JSON from {_redact_url(url)}: {e}") from e
