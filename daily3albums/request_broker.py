from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse, urlsplit, parse_qsl, urlencode, urlunsplit

import httpx
import logging


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


def _get_adapter_logger(repo_root: Path) -> logging.Logger:
    logger = logging.getLogger("adapter_requests")
    if logger.handlers:
        return logger
    logs_dir = repo_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "adapters.log"
    log_path.touch(exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_ms: int = 400
    max_delay_ms: int = 6000
    jitter: bool = True


@dataclass
class HostPolicy:
    rate_limit_rps: float = 1.0
    ttl_default_s: int = 86400
    negative_cache_ttl_s: int = 3600
    retry: RetryPolicy = field(default_factory=RetryPolicy)


@dataclass
class AdapterPolicy:
    timeout: httpx.Timeout
    retry: RetryPolicy


class BrokerRequestError(RuntimeError):
    def __init__(self, adapter_name: str | None, url: str, cause: Exception) -> None:
        self.adapter_name = adapter_name or "unknown"
        self.url = url
        self.cause = cause
        super().__init__(f"{self.adapter_name} request failed url={_redact_url(url)} cause={type(cause).__name__}: {cause}")


class RequestBroker:
    def __init__(
        self,
        repo_root: Path,
        endpoint_policies: dict,
        logger: Optional[Callable[[str], None]] = None,
        timeout_s: float = 25.0,
        connect_timeout_s: float = 10.0,
        read_timeout_s: float = 25.0,
        write_timeout_s: float = 10.0,
        pool_timeout_s: float = 10.0,
    ) -> None:
        self.repo_root = repo_root
        self.policies_raw = endpoint_policies or {}
        self.logger = logger
        self.timeout_s = float(timeout_s)
        self.connect_timeout_s = float(connect_timeout_s)
        self.read_timeout_s = float(read_timeout_s)
        self.write_timeout_s = float(write_timeout_s)
        self.pool_timeout_s = float(pool_timeout_s)
        self.adapter_logger = _get_adapter_logger(repo_root)
        self.stats: dict[str, dict[str, int]] = {}

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
            timeout=httpx.Timeout(
                timeout=self.timeout_s,
                connect=self.connect_timeout_s,
                read=self.read_timeout_s,
                write=self.write_timeout_s,
                pool=self.pool_timeout_s,
            ),
            follow_redirects=True,
        )

    def _record_stat(self, adapter_name: str | None, key: str, inc: int = 1) -> None:
        adapter = adapter_name or "unknown"
        bucket = self.stats.setdefault(adapter, {"requests": 0, "timeouts": 0, "retries": 0, "failures": 0})
        bucket[key] = int(bucket.get(key, 0)) + inc

    def get_stats_snapshot(self) -> dict[str, dict[str, int]]:
        return {k: dict(v) for k, v in self.stats.items()}

    def close(self) -> None:
        try:
            self.client.close()
        finally:
            self.conn.close()

    def _log(self, msg: str) -> None:
        if self.logger:
            self.logger(msg)

    def _log_adapter_activity(
        self,
        adapter_name: str | None,
        action: str,
        url: str,
        status: str | None = None,
        cache: str | None = None,
        sleep_s: float | None = None,
        error: str | None = None,
        details: str | None = None,
    ) -> None:
        host = ""
        try:
            host = urlparse(url).netloc
        except Exception:
            host = ""
        fields = [
            f"adapter={adapter_name or 'unknown'}",
            f"action={action}",
            f"host={host}",
            f"url={_redact_url(url)}",
        ]
        if status is not None:
            fields.append(f"status={status}")
        if cache is not None:
            fields.append(f"cache={cache}")
        if sleep_s is not None:
            fields.append(f"sleep_s={sleep_s:.3f}")
        if error is not None:
            fields.append(f"error={error}")
        if details is not None:
            fields.append(f"details={details}")
        self.adapter_logger.info(" ".join(fields))

    def _fixture_bytes(self, url: str) -> bytes | None:
        fixtures_dir = os.environ.get("DAILY3ALBUMS_FIXTURES_DIR")
        if not fixtures_dir:
            return None

        base = Path(fixtures_dir)
        if not base.is_absolute():
            base = self.repo_root / base

        map_path = base / "url_map.json"
        if not map_path.exists():
            return None

        try:
            mapping = json.loads(map_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        rel = mapping.get(url)
        if not rel:
            if os.environ.get("DAILY3ALBUMS_FIXTURES_STRICT", "").lower() in {"1", "true", "yes"}:
                raise RuntimeError(f"Fixture missing for URL: {_redact_url(url)}")
            return None

        fixture_path = (base / rel).resolve()
        if not fixture_path.exists():
            raise RuntimeError(f"Fixture file not found: {fixture_path}")

        self._log(f"FIXTURE HIT url={_redact_url(url)} path={fixture_path}")
        return fixture_path.read_bytes()

    def _host_policy(self, host: str) -> HostPolicy:
        hosts = (self.policies_raw or {}).get("hosts", {})
        h = hosts.get(host, {}) if isinstance(hosts, dict) else {}

        retry_raw = h.get("retry", {}) if isinstance(h, dict) else {}
        max_attempts_cfg = retry_raw.get("max_attempts")
        max_retries_cfg = retry_raw.get("max_retries")
        if max_retries_cfg is None and max_attempts_cfg is not None:
            try:
                max_retries_cfg = max(0, int(max_attempts_cfg) - 1)
            except Exception:
                max_retries_cfg = 2
        rp = RetryPolicy(
            max_attempts=max(1, int(max_retries_cfg if max_retries_cfg is not None else 2) + 1),
            base_delay_ms=int(retry_raw.get("base_delay_ms", 500)),
            max_delay_ms=int(retry_raw.get("max_delay_ms", 5000)),
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

    def _adapter_policy(self, adapter_name: str | None, host_policy: HostPolicy) -> AdapterPolicy:
        default_retry = host_policy.retry
        timeout = httpx.Timeout(
            timeout=self.timeout_s,
            connect=self.connect_timeout_s,
            read=self.read_timeout_s,
            write=self.write_timeout_s,
            pool=self.pool_timeout_s,
        )
        configured = ((self.policies_raw or {}).get("adapter_policies") or {}).get(adapter_name or "", {})
        default_adapter_policies = {
            "LastFmAdapter": {"timeout": {"connect": 10, "read": 25, "write": 10, "pool": 10}, "max_retries": 2},
            "MusicBrainzAdapter": {"timeout": {"connect": 10, "read": 18, "write": 10, "pool": 10}, "max_retries": 1},
        }
        base = default_adapter_policies.get(adapter_name or "", {})
        policy = {**base, **(configured if isinstance(configured, dict) else {})}
        timeout_raw = policy.get("timeout") if isinstance(policy, dict) else {}
        timeout_cfg = timeout_raw if isinstance(timeout_raw, dict) else {}

        timeout = httpx.Timeout(
            timeout=float(timeout_cfg.get("read", self.read_timeout_s)),
            connect=float(timeout_cfg.get("connect", self.connect_timeout_s)),
            read=float(timeout_cfg.get("read", self.read_timeout_s)),
            write=float(timeout_cfg.get("write", self.write_timeout_s)),
            pool=float(timeout_cfg.get("pool", self.pool_timeout_s)),
        )

        max_retries = policy.get("max_retries") if isinstance(policy, dict) else None
        if max_retries is None:
            retry = default_retry
        else:
            retry = RetryPolicy(
                max_attempts=max(1, int(max_retries) + 1),
                base_delay_ms=default_retry.base_delay_ms,
                max_delay_ms=default_retry.max_delay_ms,
                jitter=default_retry.jitter,
            )

        return AdapterPolicy(timeout=timeout, retry=retry)

    def _rate_limit(self, host: str, adapter_name: str | None, url: str) -> None:
        pol = self._host_policy(host)
        rps = max(pol.rate_limit_rps, 0.01)
        min_interval = 1.0 / rps

        now = time.monotonic()
        last = self._host_last_ts.get(host, 0.0)
        wait = (last + min_interval) - now
        if wait > 0:
            self._log(f"RATE_LIMIT host={host} sleep={wait:.3f}s")
            self._log_adapter_activity(
                adapter_name=adapter_name,
                action="rate_limit",
                url=url,
                sleep_s=wait,
            )
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

    def get(
        self,
        url: str,
        headers: Optional[dict] = None,
        ttl_override_s: Optional[int] = None,
        adapter_name: str | None = None,
    ) -> bytes | None:
        fixture_body = self._fixture_bytes(url)
        if fixture_body is not None:
            self._log_adapter_activity(
                adapter_name=adapter_name,
                action="GET",
                url=url,
                status="fixture",
                cache="hit",
            )
            return fixture_body

        parsed = urlparse(url)
        host = parsed.netloc

        key = self._cache_key(url)
        cached = self._cache_get(key)
        if cached:
            status = int(cached.get("status", 0))
            if 200 <= status <= 299:
                self._log(f"CACHE HIT url={_redact_url(url)}")
                self._log_adapter_activity(
                    adapter_name=adapter_name,
                    action="GET",
                    url=url,
                    status=str(status),
                    cache="hit",
                )
                return cached["body"]

            # 负缓存（非 2xx）保持与首次请求一致：直接抛异常
            self._log(f"CACHE HIT NEG status={status} url={_redact_url(url)}")
            self._log_adapter_activity(
                adapter_name=adapter_name,
                action="GET",
                url=url,
                status=str(status),
                cache="hit",
                error=f"HTTP_{status}",
            )
            raise RuntimeError(f"HTTP {status} for {_redact_url(url)} (cached)")

        self._log(f"CACHE MISS url={_redact_url(url)}")
        self._log_adapter_activity(
            adapter_name=adapter_name,
            action="GET",
            url=url,
            cache="miss",
        )

        pol = self._host_policy(host)
        adapter_policy = self._adapter_policy(adapter_name, pol)
        self._log_adapter_activity(
            adapter_name=adapter_name,
            action="policy",
            url=url,
            details=(
                f"timeout_connect={adapter_policy.timeout.connect} "
                f"timeout_read={adapter_policy.timeout.read} "
                f"timeout_write={adapter_policy.timeout.write} "
                f"timeout_pool={adapter_policy.timeout.pool} "
                f"max_attempts={adapter_policy.retry.max_attempts}"
            ),
        )
        ttl_ok = int(ttl_override_s) if ttl_override_s is not None else pol.ttl_default_s

        attempt = 0
        while True:
            attempt += 1
            self._record_stat(adapter_name, "requests")
            self._rate_limit(host, adapter_name=adapter_name, url=url)

            try:
                resp = self.client.get(url, headers=headers, timeout=adapter_policy.timeout)
                status = int(resp.status_code)

                if status == 429 or 500 <= status <= 599:
                    if attempt < adapter_policy.retry.max_attempts:
                        delay = min(adapter_policy.retry.max_delay_ms, adapter_policy.retry.base_delay_ms * (2 ** (attempt - 1)))
                        if adapter_policy.retry.jitter:
                            delay = int(delay * (0.6 + 0.8 * random.random()))
                        self._log(f"RETRY status={status} attempt={attempt} delay_ms={delay} url={_redact_url(url)}")
                        self._record_stat(adapter_name, "retries")
                        self._log_adapter_activity(
                            adapter_name=adapter_name,
                            action="retry",
                            url=url,
                            status=str(status),
                            sleep_s=delay / 1000.0,
                        )
                        time.sleep(delay / 1000.0)
                        continue

                body = resp.content
                hdrs = dict(resp.headers)

                if 200 <= status <= 299:
                    self._cache_put(key, url, status, hdrs, body, ttl_ok)
                    self._log_adapter_activity(
                        adapter_name=adapter_name,
                        action="GET",
                        url=url,
                        status=str(status),
                        cache="write",
                    )
                    return body

                self._cache_put(key, url, status, hdrs, body, pol.negative_cache_ttl_s)
                self._log_adapter_activity(
                    adapter_name=adapter_name,
                    action="GET",
                    url=url,
                    status=str(status),
                    cache="write-negative",
                    error=f"HTTP_{status}",
                )
                self._record_stat(adapter_name, "failures")
                self.adapter_logger.error(
                    "request_failed adapter=%s url=%s exc_type=HTTPStatusError attempts=%s",
                    adapter_name or "unknown",
                    _redact_url(url),
                    attempt,
                )
                raise BrokerRequestError(adapter_name=adapter_name, url=url, cause=RuntimeError(f"HTTP_{status}"))

            except (httpx.TimeoutException, httpx.TransportError) as e:
                if isinstance(e, httpx.TimeoutException):
                    self._record_stat(adapter_name, "timeouts")
                if attempt < adapter_policy.retry.max_attempts:
                    delay = min(adapter_policy.retry.max_delay_ms, adapter_policy.retry.base_delay_ms * (2 ** (attempt - 1)))
                    if adapter_policy.retry.jitter:
                        delay = int(delay * (0.6 + 0.8 * random.random()))
                    self._log(f"RETRY error={type(e).__name__} attempt={attempt} delay_ms={delay} url={_redact_url(url)}")
                    self._record_stat(adapter_name, "retries")
                    self._log_adapter_activity(
                        adapter_name=adapter_name,
                        action="retry",
                        url=url,
                        error=type(e).__name__,
                        sleep_s=delay / 1000.0,
                    )
                    time.sleep(delay / 1000.0)
                    continue
                self._record_stat(adapter_name, "failures")
                self.adapter_logger.error(
                    "request_failed adapter=%s url=%s exc_type=%s attempts=%s",
                    adapter_name or "unknown",
                    _redact_url(url),
                    type(e).__name__,
                    attempt,
                )
                self._log_adapter_activity(
                    adapter_name=adapter_name,
                    action="error",
                    url=url,
                    error=type(e).__name__,
                )
                raise BrokerRequestError(adapter_name=adapter_name, url=url, cause=e) from e

    def get_json(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict[str, Any]] = None,
        ttl_override_s: Optional[int] = None,
        adapter_name: str | None = None,
    ) -> Any:
        if params:
            q = urlencode([(k, str(v)) for k, v in params.items() if v is not None])
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{q}" if q else url
        raw = self.get(url, headers=headers, ttl_override_s=ttl_override_s, adapter_name=adapter_name)
        if raw is None:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Bad JSON from {_redact_url(url)}: {e}") from e
