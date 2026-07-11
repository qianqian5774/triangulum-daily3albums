#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from daily3albums.artifact_writer import OutputValidationError, validate_today


DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_ARCHIVE_RETENTION_DAYS = 7
DEFAULT_USER_AGENT = (
    "TriangulumDaily-ArchiveSeed/1.0 "
    "(+https://github.com/qianqian5774/triangulum-daily3albums)"
)


class SeedRestoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class Provider:
    name: str
    kind: str
    location: str


@dataclass
class ProviderAttempt:
    name: str
    kind: str
    location: str
    status: str
    error: str | None = None
    effective_url: str | None = None
    dates: int = 0
    files: int = 0


@dataclass
class RestoreSummary:
    status: str
    provider: str | None
    provider_kind: str | None
    effective_url: str | None
    dates: int
    files: int
    out_dir: str
    attempts: list[ProviderAttempt] = field(default_factory=list)


def _project_pages_base_url() -> str:
    repository = os.getenv("GITHUB_REPOSITORY", "qianqian5774/triangulum-daily3albums")
    owner, _, repo = repository.partition("/")
    if owner and repo:
        return f"https://{owner}.github.io/{repo}/"
    return "https://qianqian5774.github.io/triangulum-daily3albums/"


def _pages_base_url() -> str:
    explicit = os.getenv("DAILY3ALBUMS_PAGES_BASE_URL", "").strip()
    return explicit.rstrip("/") + "/" if explicit else _project_pages_base_url()


def _default_providers(local_dirs: list[Path] | None = None) -> list[Provider]:
    providers: list[Provider] = []
    explicit = os.getenv("DAILY3ALBUMS_PAGES_BASE_URL", "").strip()
    if explicit:
        providers.append(Provider("custom-domain", "http", explicit.rstrip("/") + "/"))
    project_url = _project_pages_base_url()
    if not explicit or project_url.rstrip("/") != explicit.rstrip("/"):
        providers.append(Provider("github-pages-project", "http", project_url))
    for index, path in enumerate(local_dirs or []):
        providers.append(Provider(f"local-{index + 1}", "local", str(path)))
    return providers


def _sort_key(item: dict[str, Any]) -> str:
    run_at = item.get("run_at")
    if isinstance(run_at, str):
        return run_at
    return f"{item.get('date','')}-{item.get('run_id','')}"


def _is_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _select_recent_unique_dates(items: list[Any], max_days: int) -> list[dict[str, Any]]:
    valid_items = [
        item
        for item in items
        if isinstance(item, dict)
        and _is_date(item.get("date"))
        and isinstance(item.get("run_id"), str)
        and item.get("run_id", "").strip()
    ]
    sorted_items = sorted(valid_items, key=_sort_key, reverse=True)
    selected: list[dict[str, Any]] = []
    seen_dates: set[str] = set()
    for item in sorted_items:
        date = item["date"]
        if date in seen_dates:
            continue
        seen_dates.add(date)
        selected.append(item)
        if len(selected) >= max_days:
            break
    return selected


def _decode_json(data: bytes, source: str) -> Any:
    stripped = data.lstrip()
    if stripped.startswith((b"<!DOCTYPE html", b"<html", b"<HTML")):
        raise SeedRestoreError(f"HTML response is not valid archive seed JSON: {source}")
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SeedRestoreError(f"invalid JSON from {source}: {exc}") from exc


def _validate_index(index: Any, source: str, max_days: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(index, dict):
        raise SeedRestoreError(f"index must be an object: {source}")
    items = index.get("items")
    if not isinstance(items, list):
        raise SeedRestoreError(f"index.items must be a list: {source}")
    selected = _select_recent_unique_dates(items, max_days=max_days)
    if items and not selected:
        raise SeedRestoreError(f"index contains no valid date/run_id entries: {source}")
    return index, selected


def _validate_archive(data: bytes, item: dict[str, Any], source: str) -> None:
    payload = _decode_json(data, source)
    if not isinstance(payload, dict):
        raise SeedRestoreError(f"archive payload must be an object: {source}")
    if payload.get("date") != item.get("date"):
        raise SeedRestoreError(
            f"archive date mismatch at {source}: index={item.get('date')} payload={payload.get('date')}"
        )
    if payload.get("run_id") != item.get("run_id"):
        raise SeedRestoreError(
            f"archive run_id mismatch at {source}: "
            f"index={item.get('run_id')} payload={payload.get('run_id')}"
        )
    try:
        validate_today(payload)
    except OutputValidationError as exc:
        raise SeedRestoreError(f"archive issue schema invalid at {source}: {exc}") from exc


def _http_read(url: str) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            status = int(getattr(response, "status", response.getcode()))
            content_type = response.headers.get_content_type()
            effective_url = response.geturl()
            data = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise SeedRestoreError(f"request failed url={url}: {exc}") from exc
    if status < 200 or status >= 300:
        raise SeedRestoreError(f"unexpected HTTP status={status} url={url}")
    if content_type not in {"application/json", "text/json"} and not content_type.endswith("+json"):
        raise SeedRestoreError(f"unexpected Content-Type={content_type!r} url={url}")
    if not data.strip():
        raise SeedRestoreError(f"empty response url={url}")
    return data, content_type, effective_url


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _archive_candidate_paths(item: dict[str, Any]) -> list[str]:
    date = item["date"]
    run_id = item["run_id"]
    return [f"data/archive/{date}/{run_id}.json", f"data/archive/{date}.json"]


def _materialize_http_provider(
    provider: Provider,
    destination: Path,
    max_days: int,
) -> tuple[list[dict[str, Any]], int, str]:
    base_url = provider.location.rstrip("/") + "/"
    index_url = urllib.parse.urljoin(base_url, "data/index.json")
    index_bytes, _content_type, effective_url = _http_read(index_url)
    index, selected = _validate_index(_decode_json(index_bytes, index_url), index_url, max_days)
    files = 0
    archive_dir = destination / "archive"
    for item in selected:
        errors: list[str] = []
        archive_bytes: bytes | None = None
        source = ""
        for remote_path in _archive_candidate_paths(item):
            url = urllib.parse.urljoin(base_url, remote_path)
            try:
                candidate, _type, _effective = _http_read(url)
                _validate_archive(candidate, item, url)
                archive_bytes = candidate
                source = url
                break
            except SeedRestoreError as exc:
                errors.append(str(exc))
        if archive_bytes is None:
            raise SeedRestoreError(
                f"no valid archive JSON for date={item['date']} run_id={item['run_id']}: "
                + " | ".join(errors)
            )
        date = item["date"]
        run_id = item["run_id"]
        _write_bytes(archive_dir / date / f"{run_id}.json", archive_bytes)
        _write_bytes(archive_dir / f"{date}.json", archive_bytes)
        files += 2
        print(f"archive_seed fetch=ok provider={provider.name} source={source}")
    _write_index(destination, index, selected, max_days)
    return selected, files, effective_url


def _resolve_local_data_dir(location: str) -> Path:
    path = Path(location)
    if (path / "index.json").is_file():
        return path
    if (path / "data" / "index.json").is_file():
        return path / "data"
    return path


def _materialize_local_provider(
    provider: Provider,
    destination: Path,
    max_days: int,
) -> tuple[list[dict[str, Any]], int, str | None]:
    source_dir = _resolve_local_data_dir(provider.location)
    index_path = source_dir / "index.json"
    if not index_path.is_file():
        raise SeedRestoreError(f"local index missing: {index_path}")
    index = _decode_json(index_path.read_bytes(), str(index_path))
    index, selected = _validate_index(index, str(index_path), max_days)
    files = 0
    archive_dir = destination / "archive"
    for item in selected:
        candidates = [source_dir / path.removeprefix("data/") for path in _archive_candidate_paths(item)]
        existing = next((path for path in candidates if path.is_file()), None)
        if existing is None:
            raise SeedRestoreError(
                f"local archive missing for date={item['date']} run_id={item['run_id']}"
            )
        archive_bytes = existing.read_bytes()
        _validate_archive(archive_bytes, item, str(existing))
        date = item["date"]
        run_id = item["run_id"]
        _write_bytes(archive_dir / date / f"{run_id}.json", archive_bytes)
        _write_bytes(archive_dir / f"{date}.json", archive_bytes)
        files += 2
    _write_index(destination, index, selected, max_days)
    return selected, files, None


def _write_index(
    destination: Path,
    original_index: dict[str, Any],
    selected: list[dict[str, Any]],
    max_days: int,
) -> None:
    seed_index = {
        "output_schema_version": str(original_index.get("output_schema_version") or "1"),
        "archive_retention_days": max_days,
        "items": selected,
    }
    (destination / "index.json").write_text(
        json.dumps(seed_index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_baseline(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    payload = _decode_json(path.read_bytes(), str(path))
    if not isinstance(payload, dict):
        raise SeedRestoreError(f"baseline must be an object: {path}")
    return payload


def _check_baseline(
    selected: list[dict[str, Any]],
    baseline: dict[str, Any] | None,
    allow_empty_history: bool,
) -> None:
    count = len(selected)
    if count == 0 and not allow_empty_history:
        raise SeedRestoreError("empty archive history requires explicit --allow-empty-history")
    if baseline is None:
        return
    previous = baseline.get("date_count")
    if isinstance(previous, int) and count < previous:
        raise SeedRestoreError(f"archive date count regressed from baseline={previous} to restored={count}")


def _promote_directory(staged: Path, out_dir: Path) -> None:
    backup = out_dir.parent / f".{out_dir.name}.restore-backup"
    if backup.exists():
        shutil.rmtree(backup)
    had_existing = out_dir.exists()
    if had_existing:
        os.replace(out_dir, backup)
    try:
        os.replace(staged, out_dir)
    except Exception:
        if had_existing and backup.exists() and not out_dir.exists():
            os.replace(backup, out_dir)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def _write_baseline(path: Path | None, selected: list[dict[str, Any]], provider: Provider) -> None:
    if path is None:
        return
    payload = {
        "date_count": len(selected),
        "dates": [item["date"] for item in selected],
        "provider": provider.name,
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _write_summary(path: Path | None, summary: RestoreSummary) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _append_github_summary(summary: RestoreSummary) -> None:
    raw = os.getenv("GITHUB_STEP_SUMMARY", "").strip()
    if not raw:
        return
    lines = [
        "## Archive seed restore",
        "",
        f"- Status: `{summary.status}`",
        f"- Provider: `{summary.provider or 'none'}`",
        f"- Provider kind: `{summary.provider_kind or 'none'}`",
        f"- Effective URL: `{summary.effective_url or 'n/a'}`",
        f"- Restored dates: `{summary.dates}`",
        f"- Restored files: `{summary.files}`",
        "",
        "| Provider | Kind | Status | Dates | Files | Error |",
        "|---|---|---:|---:|---:|---|",
    ]
    for attempt in summary.attempts:
        error = (attempt.error or "").replace("|", "\\|")
        lines.append(
            f"| {attempt.name} | {attempt.kind} | {attempt.status} | "
            f"{attempt.dates} | {attempt.files} | {error} |"
        )
    with open(raw, "a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def restore_static_archive_seed(
    out_dir: Path,
    max_days: int,
    providers: list[Provider],
    baseline_path: Path | None = None,
    summary_path: Path | None = None,
    allow_empty_history: bool = False,
) -> RestoreSummary:
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    attempts: list[ProviderAttempt] = []
    try:
        baseline = _load_baseline(baseline_path)
    except SeedRestoreError as exc:
        summary = RestoreSummary("fail", None, None, None, 0, 0, str(out_dir), attempts)
        attempts.append(ProviderAttempt("baseline", "local", str(baseline_path), "fail", str(exc)))
        _write_summary(summary_path, summary)
        _append_github_summary(summary)
        return summary

    for index, provider in enumerate(providers):
        staged = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.restore-", dir=out_dir.parent))
        try:
            materialize: Callable[..., tuple[list[dict[str, Any]], int, str | None]]
            materialize = (
                _materialize_http_provider if provider.kind == "http" else _materialize_local_provider
            )
            selected, files, effective_url = materialize(provider, staged, max_days)
            _check_baseline(selected, baseline, allow_empty_history)
            _promote_directory(staged, out_dir)
            _write_baseline(baseline_path, selected, provider)
            attempt = ProviderAttempt(
                provider.name,
                provider.kind,
                provider.location,
                "ok",
                effective_url=effective_url,
                dates=len(selected),
                files=files,
            )
            attempts.append(attempt)
            status = "healthy" if index == 0 else "degraded"
            summary = RestoreSummary(
                status,
                provider.name,
                provider.kind,
                effective_url,
                len(selected),
                files,
                str(out_dir),
                attempts,
            )
            _write_summary(summary_path, summary)
            _append_github_summary(summary)
            print(
                f"archive_seed status={status} provider={provider.name} kind={provider.kind} "
                f"dates={len(selected)} files={files} effective_url={effective_url or 'n/a'} out={out_dir}"
            )
            return summary
        except (OSError, SeedRestoreError) as exc:
            attempts.append(
                ProviderAttempt(provider.name, provider.kind, provider.location, "fail", str(exc))
            )
            print(
                f"archive_seed provider={provider.name} status=failed error={exc}",
                file=sys.stderr,
            )
        finally:
            if staged.exists():
                shutil.rmtree(staged)

    summary = RestoreSummary("fail", None, None, None, 0, 0, str(out_dir), attempts)
    _write_summary(summary_path, summary)
    _append_github_summary(summary)
    print("archive_seed status=fail providers_exhausted=true", file=sys.stderr)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore and validate recent published archive JSON as a static build seed."
    )
    parser.add_argument("--out", default=".state/pages-history-seed/data")
    parser.add_argument("--max-days", type=int, default=DEFAULT_ARCHIVE_RETENTION_DAYS)
    parser.add_argument("--provider-url", action="append", default=[])
    parser.add_argument("--local-dir", action="append", default=[])
    parser.add_argument(
        "--prefer-local",
        action="store_true",
        help="Try local providers before HTTP providers for explicit recovery runs",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Use only local providers; intended for recovery inspection and fixtures",
    )
    parser.add_argument("--baseline", default=".state/pages-history-baseline.json")
    parser.add_argument("--summary", default=".state/pages-history-seed-summary.json")
    parser.add_argument("--allow-empty-history", action="store_true")
    args = parser.parse_args()

    max_days = max(0, args.max_days)
    if max_days == 0:
        print("archive_seed status=skip max_days=0")
        return 0

    http_providers = [
        Provider(f"http-{index + 1}", "http", url.rstrip("/") + "/")
        for index, url in enumerate(args.provider_url)
    ]
    if not http_providers and not args.local_only:
        http_providers.extend(_default_providers())
    local_providers = [
        Provider(f"local-{index + 1}", "local", location)
        for index, location in enumerate(args.local_dir)
    ]
    providers = (
        local_providers
        if args.local_only
        else local_providers + http_providers
        if args.prefer_local
        else http_providers + local_providers
    )
    if not providers:
        print("archive_seed status=fail reason=no_providers", file=sys.stderr)
        return 2

    summary = restore_static_archive_seed(
        Path(args.out),
        max_days=max_days,
        providers=providers,
        baseline_path=Path(args.baseline) if args.baseline else None,
        summary_path=Path(args.summary) if args.summary else None,
        allow_empty_history=args.allow_empty_history,
    )
    return 0 if summary.status in {"healthy", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
