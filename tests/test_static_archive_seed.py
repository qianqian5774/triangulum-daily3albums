from __future__ import annotations

import json
from email.message import Message
from pathlib import Path

import pytest

from scripts import restore_static_archive_seed as restore
from scripts.restore_static_archive_seed import (
    DEFAULT_USER_AGENT,
    Provider,
    _default_providers,
    _pages_base_url,
    _select_recent_unique_dates,
    restore_static_archive_seed,
)


def _pick(slot: str, index: int) -> dict:
    return {
        "slot": slot,
        "rg_mbid": f"00000000-0000-0000-0000-{index:012d}",
        "cover": {"optimized_cover_url": "assets/placeholder.svg"},
    }


def _issue(date: str, run_id: str) -> dict:
    slots = []
    labels = ["06:00-11:59", "12:00-17:59", "18:00-23:59"]
    roles = ["Headliner", "Lineage", "DeepCut"]
    for slot_id, label in enumerate(labels):
        slots.append(
            {
                "slot_id": slot_id,
                "window_label": label,
                "picks": [_pick(role, slot_id * 3 + index + 1) for index, role in enumerate(roles)],
            }
        )
    return {
        "output_schema_version": "1.0",
        "date": date,
        "run_id": run_id,
        "run_at": f"{date}T06:00:00+08:00",
        "theme_of_day": "auto",
        "slots": slots,
    }


def _write_seed(root: Path, issues: list[dict]) -> Path:
    data_dir = root / "data"
    items = []
    for issue in issues:
        date = issue["date"]
        run_id = issue["run_id"]
        payload = json.dumps(issue, ensure_ascii=False, indent=2).encode("utf-8")
        path = data_dir / "archive" / date / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        items.append(
            {
                "date": date,
                "run_id": run_id,
                "run_at": issue["run_at"],
                "theme_of_day": issue["theme_of_day"],
            }
        )
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "index.json").write_text(
        json.dumps(
            {
                "output_schema_version": "1.0",
                "archive_retention_days": 7,
                "items": items,
            }
        ),
        encoding="utf-8",
    )
    return data_dir


def test_pages_base_url_uses_explicit_custom_domain_override(monkeypatch):
    monkeypatch.setenv("DAILY3ALBUMS_PAGES_BASE_URL", "https://triangulumdaily.space")
    assert _pages_base_url() == "https://triangulumdaily.space/"


def test_default_providers_keep_project_pages_fallback(monkeypatch):
    monkeypatch.setenv("DAILY3ALBUMS_PAGES_BASE_URL", "https://triangulumdaily.space")
    monkeypatch.setenv("GITHUB_REPOSITORY", "qianqian5774/triangulum-daily3albums")
    providers = _default_providers()
    assert [(provider.name, provider.location) for provider in providers] == [
        ("custom-domain", "https://triangulumdaily.space/"),
        ("github-pages-project", "https://qianqian5774.github.io/triangulum-daily3albums/"),
    ]


def test_select_recent_unique_dates_prefers_latest_run_per_day():
    items = [
        {"date": "2026-06-24", "run_id": "morning", "run_at": "2026-06-24T06:00:00+08:00"},
        {"date": "2026-06-25", "run_id": "morning", "run_at": "2026-06-25T06:00:00+08:00"},
        {"date": "2026-06-25", "run_id": "manual", "run_at": "2026-06-25T12:00:00+08:00"},
        {"date": "bad-date", "run_id": "invalid", "run_at": "later"},
    ]
    selected = _select_recent_unique_dates(items, max_days=3)
    assert [(item["date"], item["run_id"]) for item in selected] == [
        ("2026-06-25", "manual"),
        ("2026-06-24", "morning"),
    ]


def test_local_provider_validates_and_promotes_seed(tmp_path):
    source = _write_seed(
        tmp_path / "source",
        [_issue("2026-06-24", "older"), _issue("2026-06-25", "newer")],
    )
    out = tmp_path / "out" / "data"
    summary = restore_static_archive_seed(
        out,
        max_days=7,
        providers=[Provider("fixture", "local", str(source))],
        baseline_path=tmp_path / "baseline.json",
        summary_path=tmp_path / "summary.json",
    )
    assert summary.status == "healthy"
    assert summary.dates == 2
    assert (out / "archive" / "2026-06-25" / "newer.json").is_file()
    assert (out / "archive" / "2026-06-25.json").is_file()
    assert json.loads((tmp_path / "baseline.json").read_text(encoding="utf-8"))["date_count"] == 2


def test_failed_provider_falls_back_to_existing_local_seed(tmp_path, monkeypatch):
    source = _write_seed(tmp_path / "source", [_issue("2026-06-25", "published")])

    def fail_http(_url: str):
        raise restore.SeedRestoreError("HTTP 403 from Browser Integrity Check")

    monkeypatch.setattr(restore, "_http_read", fail_http)
    summary = restore_static_archive_seed(
        tmp_path / "out" / "data",
        max_days=7,
        providers=[
            Provider("custom-domain", "http", "https://triangulumdaily.space/"),
            Provider("last-good", "local", str(source)),
        ],
    )
    assert summary.status == "degraded"
    assert summary.provider == "last-good"
    assert summary.attempts[0].status == "fail"
    assert "403" in (summary.attempts[0].error or "")


@pytest.mark.parametrize(
    ("index_bytes", "content_type", "error_fragment"),
    [
        (b"<html>challenge</html>", "text/html", "Content-Type"),
        (b"not json", "application/json", "invalid JSON"),
    ],
)
def test_invalid_http_index_does_not_replace_existing_seed(
    tmp_path, monkeypatch, index_bytes, content_type, error_fragment
):
    out = tmp_path / "out" / "data"
    out.mkdir(parents=True)
    marker = out / "keep.txt"
    marker.write_text("preserve me", encoding="utf-8")

    def fake_http(_url: str):
        if content_type != "application/json":
            raise restore.SeedRestoreError(f"unexpected Content-Type='{content_type}'")
        return index_bytes, content_type, "https://triangulumdaily.space/data/index.json"

    monkeypatch.setattr(restore, "_http_read", fake_http)
    summary = restore_static_archive_seed(
        out,
        max_days=7,
        providers=[Provider("custom-domain", "http", "https://triangulumdaily.space/")],
    )
    assert summary.status == "fail"
    assert error_fragment in (summary.attempts[0].error or "")
    assert marker.read_text(encoding="utf-8") == "preserve me"


def test_missing_archive_file_is_fatal_and_preserves_existing_seed(tmp_path, monkeypatch):
    issue = _issue("2026-06-25", "published")
    index = json.dumps(
        {"output_schema_version": "1.0", "items": [{key: issue[key] for key in ("date", "run_id", "run_at")}]}
    ).encode()
    out = tmp_path / "out" / "data"
    out.mkdir(parents=True)
    (out / "keep.txt").write_text("old", encoding="utf-8")

    def fake_http(url: str):
        if url.endswith("data/index.json"):
            return index, "application/json", url
        raise restore.SeedRestoreError("HTTP 404")

    monkeypatch.setattr(restore, "_http_read", fake_http)
    summary = restore_static_archive_seed(
        out,
        max_days=7,
        providers=[Provider("custom-domain", "http", "https://triangulumdaily.space/")],
    )
    assert summary.status == "fail"
    assert "no valid archive JSON" in (summary.attempts[0].error or "")
    assert (out / "keep.txt").read_text(encoding="utf-8") == "old"


def test_baseline_blocks_date_count_regression(tmp_path):
    source = _write_seed(tmp_path / "source", [_issue("2026-06-25", "only-one")])
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"date_count": 3}), encoding="utf-8")
    out = tmp_path / "out" / "data"
    out.mkdir(parents=True)
    (out / "keep.txt").write_text("old", encoding="utf-8")
    summary = restore_static_archive_seed(
        out,
        max_days=7,
        providers=[Provider("local", "local", str(source))],
        baseline_path=baseline,
    )
    assert summary.status == "fail"
    assert "regressed" in (summary.attempts[0].error or "")
    assert (out / "keep.txt").read_text(encoding="utf-8") == "old"


def test_empty_history_requires_explicit_override(tmp_path):
    source = tmp_path / "source" / "data"
    source.mkdir(parents=True)
    (source / "index.json").write_text(
        json.dumps({"output_schema_version": "1.0", "items": []}), encoding="utf-8"
    )
    denied = restore_static_archive_seed(
        tmp_path / "denied" / "data",
        max_days=7,
        providers=[Provider("empty", "local", str(source))],
    )
    allowed = restore_static_archive_seed(
        tmp_path / "allowed" / "data",
        max_days=7,
        providers=[Provider("empty", "local", str(source))],
        allow_empty_history=True,
    )
    assert denied.status == "fail"
    assert allowed.status == "healthy"


def test_http_read_sets_descriptive_user_agent(monkeypatch):
    captured = {}

    class Response:
        status = 200

        def __init__(self):
            self.headers = Message()
            self.headers["Content-Type"] = "application/json; charset=utf-8"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def getcode(self):
            return self.status

        def geturl(self):
            return "https://triangulumdaily.space/data/index.json"

        def read(self):
            return b'{"items": []}'

    def fake_urlopen(request, timeout):
        captured["user_agent"] = request.get_header("User-agent")
        captured["accept"] = request.get_header("Accept")
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(restore.urllib.request, "urlopen", fake_urlopen)
    restore._http_read("https://triangulumdaily.space/data/index.json")
    assert captured == {
        "user_agent": DEFAULT_USER_AGENT,
        "accept": "application/json",
        "timeout": restore.DEFAULT_TIMEOUT_SECONDS,
    }
