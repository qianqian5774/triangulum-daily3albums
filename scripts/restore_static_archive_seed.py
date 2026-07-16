#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from daily3albums.public_contract import (
    PublicContractError,
    require_byte_identical,
    validate_archive,
    validate_archive_identity,
    validate_index,
)
from daily3albums.request_broker import redact_url
from daily3albums.runtime_outcomes import (
    OutcomeCode,
    outcome_code_for_contract_error,
    outcome_code_for_http_status,
)


DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_ARCHIVE_RETENTION_DAYS = 7
DEFAULT_USER_AGENT = (
    "TriangulumDaily-ArchiveSeed/1.0 "
    "(+https://github.com/qianqian5774/triangulum-daily3albums)"
)


def _safe_location(kind: str, location: str) -> str:
    return redact_url(location) if kind == "http" else location


class SeedRestoreError(RuntimeError):
    def __init__(
        self,
        code: OutcomeCode,
        *,
        stage: str,
        resource: str,
        detail: str | None = None,
        http_status: int | None = None,
        date_key: str | None = None,
        run_id: str | None = None,
    ) -> None:
        self.code = code.value
        self.stage = stage
        self.resource = resource
        self.http_status = http_status
        self.date_key = date_key
        self.run_id = run_id
        fields = [f"code={self.code}", f"stage={stage}", f"resource={resource}"]
        if http_status is not None:
            fields.append(f"http_status={http_status}")
        if date_key:
            fields.append(f"date={date_key}")
        if run_id:
            fields.append(f"run_id={run_id}")
        if detail:
            fields.append(f"detail={detail}")
        super().__init__(" ".join(fields))


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
    code: str
    error: str | None = None
    effective_url: str | None = None
    dates: int = 0
    files: int = 0


@dataclass
class RestoreSummary:
    status: str
    code: str
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
        raise SeedRestoreError(
            OutcomeCode.CORRUPT,
            stage="decode_json",
            resource="archive_seed_json",
            detail="html_response",
        )
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SeedRestoreError(
            OutcomeCode.CORRUPT,
            stage="decode_json",
            resource="archive_seed_json",
            detail="json_decode_failed",
        ) from exc


def _validate_index(index: Any, source: str, max_days: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        validated = validate_index(index)
    except PublicContractError as exc:
        raise SeedRestoreError(
            outcome_code_for_contract_error(exc.code),
            stage="validate_index",
            resource="archive_seed_index",
            detail=f"contract_code:{exc.code}",
        ) from exc
    items = validated["items"]
    selected = _select_recent_unique_dates(items, max_days=max_days)
    if items and not selected:
        raise SeedRestoreError(
            OutcomeCode.INVALID_SCHEMA,
            stage="select_index_entries",
            resource="archive_seed_index",
            detail="no_valid_entries",
        )
    return validated, selected


def _validate_archive(data: bytes, item: dict[str, Any], source: str) -> None:
    payload = _decode_json(data, source)
    try:
        validated, _profile = validate_archive(payload)
        validate_archive_identity(validated, date=item["date"], run_id=item["run_id"])
    except PublicContractError as exc:
        raise SeedRestoreError(
            outcome_code_for_contract_error(exc.code),
            stage="validate_archive",
            resource="archive_seed_archive",
            detail=f"contract_code:{exc.code}",
            date_key=item.get("date"),
            run_id=item.get("run_id"),
        ) from exc


def _is_missing_http_error(error: SeedRestoreError) -> bool:
    return error.code in {OutcomeCode.MISSING.value, OutcomeCode.PROVIDER_NOT_FOUND.value}


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
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        raise SeedRestoreError(
            outcome_code_for_http_status(status),
            stage="http_read",
            resource="archive_seed_resource",
            http_status=status,
        ) from exc
    except urllib.error.URLError as exc:
        code = (
            OutcomeCode.TIMEOUT
            if isinstance(exc.reason, (TimeoutError, socket.timeout))
            else OutcomeCode.REQUEST_FAILED
        )
        raise SeedRestoreError(
            code,
            stage="http_read",
            resource="archive_seed_resource",
            detail=f"cause_type:{type(exc.reason).__name__}",
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise SeedRestoreError(
            OutcomeCode.TIMEOUT,
            stage="http_read",
            resource="archive_seed_resource",
            detail=f"cause_type:{type(exc).__name__}",
        ) from exc
    if status < 200 or status >= 300:
        raise SeedRestoreError(
            outcome_code_for_http_status(status),
            stage="http_read",
            resource="archive_seed_resource",
            http_status=status,
        )
    if content_type not in {"application/json", "text/json"} and not content_type.endswith("+json"):
        raise SeedRestoreError(
            OutcomeCode.CORRUPT,
            stage="http_read",
            resource="archive_seed_resource",
            detail="invalid_content_type",
        )
    if not data.strip():
        raise SeedRestoreError(
            OutcomeCode.CORRUPT,
            stage="http_read",
            resource="archive_seed_resource",
            detail="empty_response",
        )
    return data, content_type, redact_url(effective_url)


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
        valid_candidates: list[tuple[bytes, str]] = []
        non_missing_error: SeedRestoreError | None = None
        for remote_path in _archive_candidate_paths(item):
            url = urllib.parse.urljoin(base_url, remote_path)
            try:
                candidate, _type, _effective = _http_read(url)
                _validate_archive(candidate, item, url)
                valid_candidates.append((candidate, redact_url(url)))
            except SeedRestoreError as exc:
                if not _is_missing_http_error(exc):
                    non_missing_error = exc
        if not valid_candidates:
            if non_missing_error is not None:
                raise non_missing_error
            raise SeedRestoreError(
                OutcomeCode.MISSING,
                stage="materialize_archive",
                resource="archive_seed_archive",
                date_key=item["date"],
                run_id=item["run_id"],
            )
        if non_missing_error is not None:
            raise non_missing_error
        if len(valid_candidates) == 2:
            try:
                require_byte_identical(valid_candidates[0][0], valid_candidates[1][0])
            except PublicContractError as exc:
                raise SeedRestoreError(
                    outcome_code_for_contract_error(exc.code),
                    stage="validate_archive_alias",
                    resource="archive_seed_archive_alias",
                    detail=f"contract_code:{exc.code}",
                    date_key=item["date"],
                    run_id=item["run_id"],
                ) from exc
        archive_bytes, source = valid_candidates[0]
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
        raise SeedRestoreError(
            OutcomeCode.MISSING,
            stage="load_local_index",
            resource="archive_seed_index",
        )
    index = _decode_json(index_path.read_bytes(), str(index_path))
    index, selected = _validate_index(index, str(index_path), max_days)
    files = 0
    archive_dir = destination / "archive"
    for item in selected:
        candidates = [source_dir / path.removeprefix("data/") for path in _archive_candidate_paths(item)]
        existing = [path for path in candidates if path.is_file()]
        if not existing:
            raise SeedRestoreError(
                OutcomeCode.MISSING,
                stage="materialize_archive",
                resource="archive_seed_archive",
                date_key=item["date"],
                run_id=item["run_id"],
            )
        archive_bytes_by_path = [(path.read_bytes(), path) for path in existing]
        for candidate_bytes, path in archive_bytes_by_path:
            _validate_archive(candidate_bytes, item, str(path))
        if len(archive_bytes_by_path) == 2:
            try:
                require_byte_identical(archive_bytes_by_path[0][0], archive_bytes_by_path[1][0])
            except PublicContractError as exc:
                raise SeedRestoreError(
                    outcome_code_for_contract_error(exc.code),
                    stage="validate_archive_alias",
                    resource="archive_seed_archive_alias",
                    detail=f"contract_code:{exc.code}",
                    date_key=item["date"],
                    run_id=item["run_id"],
                ) from exc
        archive_bytes = archive_bytes_by_path[0][0]
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
        "output_schema_version": original_index["output_schema_version"],
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
        raise SeedRestoreError(
            OutcomeCode.INVALID_SCHEMA,
            stage="load_baseline",
            resource="archive_seed_baseline",
            detail="object_required",
        )
    return payload


def _check_baseline(
    selected: list[dict[str, Any]],
    baseline: dict[str, Any] | None,
    allow_empty_history: bool,
) -> None:
    count = len(selected)
    if count == 0 and not allow_empty_history:
        raise SeedRestoreError(
            OutcomeCode.LEGITIMATE_EMPTY,
            stage="baseline_policy",
            resource="archive_seed_history",
            detail="explicit_allow_empty_required",
        )
    if baseline is None:
        return
    previous = baseline.get("date_count")
    if isinstance(previous, int) and count < previous:
        raise SeedRestoreError(
            OutcomeCode.INVALID_SCHEMA,
            stage="baseline_policy",
            resource="archive_seed_baseline",
            detail=f"date_count_regression:{previous}:{count}",
        )


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
        f"- Code: `{summary.code}`",
        f"- Provider: `{summary.provider or 'none'}`",
        f"- Provider kind: `{summary.provider_kind or 'none'}`",
        f"- Effective URL: `{summary.effective_url or 'n/a'}`",
        f"- Restored dates: `{summary.dates}`",
        f"- Restored files: `{summary.files}`",
        "",
        "| Provider | Kind | Status | Code | Dates | Files | Error |",
        "|---|---|---:|---|---:|---:|---|",
    ]
    for attempt in summary.attempts:
        error = (attempt.error or "").replace("|", "\\|")
        lines.append(
            f"| {attempt.name} | {attempt.kind} | {attempt.status} | {attempt.code} | "
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
        attempts.append(
            ProviderAttempt(
                "baseline",
                "local",
                str(baseline_path),
                "fail",
                exc.code,
                str(exc),
            )
        )
        summary = RestoreSummary(
            "fail",
            exc.code,
            None,
            None,
            None,
            0,
            0,
            str(out_dir),
            attempts,
        )
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
                _safe_location(provider.kind, provider.location),
                "ok",
                (
                    OutcomeCode.LEGITIMATE_EMPTY.value
                    if not selected
                    else OutcomeCode.FALLBACK_USED.value
                    if index > 0
                    else OutcomeCode.SUCCESS.value
                ),
                effective_url=effective_url,
                dates=len(selected),
                files=files,
            )
            attempts.append(attempt)
            status = "healthy" if index == 0 else "degraded"
            summary = RestoreSummary(
                status,
                attempt.code,
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
            code = exc.code if isinstance(exc, SeedRestoreError) else OutcomeCode.UNAVAILABLE.value
            safe_error = str(exc) if isinstance(exc, SeedRestoreError) else (
                f"code={code} stage=provider_restore resource=archive_seed cause_type={type(exc).__name__}"
            )
            attempts.append(
                ProviderAttempt(
                    provider.name,
                    provider.kind,
                    _safe_location(provider.kind, provider.location),
                    "fail",
                    code,
                    safe_error,
                )
            )
            print(
                f"archive_seed provider={provider.name} status=failed {safe_error}",
                file=sys.stderr,
            )
        finally:
            if staged.exists():
                shutil.rmtree(staged)

    summary = RestoreSummary(
        "fail",
        OutcomeCode.RECOVERY_EXHAUSTED.value,
        None,
        None,
        None,
        0,
        0,
        str(out_dir),
        attempts,
    )
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
