from __future__ import annotations

import json
from pathlib import Path

from scripts.build_metrics import (
    collect_public_metrics,
    default_metrics_dir,
    format_bytes,
    start_metrics,
    summarize,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _issue(date: str, run_id: str) -> dict:
    return {
        "date": date,
        "run_id": run_id,
        "slots": [
            {"slot_id": slot_id, "picks": [{"title": f"{date}-{slot_id}-{idx}"} for idx in range(3)]}
            for slot_id in range(3)
        ],
        "picks": [{"title": "current"}],
    }


def test_format_bytes_uses_human_units():
    assert format_bytes(999) == "999 B"
    assert format_bytes(1536) == "1.50 KB"


def test_collect_public_metrics_counts_archive_and_today(tmp_path: Path):
    public = tmp_path / "public"
    data = public / "data"
    _write_json(data / "today.json", _issue("2026-06-25", "today"))
    _write_json(
        data / "index.json",
        {
            "output_schema_version": "1",
            "archive_retention_days": 7,
            "items": [
                {"date": "2026-06-25", "run_id": "today"},
                {"date": "2026-06-24", "run_id": "older"},
            ],
        },
    )
    _write_json(data / "archive" / "2026-06-25" / "today.json", _issue("2026-06-25", "today"))
    _write_json(data / "archive" / "2026-06-24.json", _issue("2026-06-24", "older"))

    metrics = collect_public_metrics(public)

    assert metrics["archive_retention_days"] == 7
    assert metrics["archive_day_count"] == 2
    assert metrics["archive_album_count"] == 18
    assert metrics["today_album_count"] == 9
    assert metrics["archive_missing_days"] == []
    assert metrics["public_size_bytes"] > 0


def test_default_metrics_dir_uses_runner_temp_for_github_runs(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DAILY3ALBUMS_BUILD_METRICS_DIR", raising=False)
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")

    assert default_metrics_dir() == tmp_path / "daily3albums-build-metrics" / "12345-2"


def test_start_metrics_resets_previous_rows(tmp_path: Path):
    metrics_dir = tmp_path / "metrics"
    _write_json(metrics_dir / "start.json", {"started_at_ms": 1})
    _write_jsonl(metrics_dir / "steps.jsonl", [{"name": "old"}])
    _write_json(metrics_dir / "build-metrics.json", {"old": True})

    assert start_metrics(metrics_dir) == 0

    assert (metrics_dir / "start.json").exists()
    assert not (metrics_dir / "steps.jsonl").exists()
    assert not (metrics_dir / "build-metrics.json").exists()


def test_summarize_ignores_stale_rows_from_another_github_run(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GITHUB_RUN_ID", "new-run")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")

    metrics_dir = tmp_path / "metrics"
    public = tmp_path / "public"
    out = tmp_path / "build-metrics.json"
    assert start_metrics(metrics_dir) == 0
    _write_jsonl(
        metrics_dir / "steps.jsonl",
        [
            {
                "name": "stale cached step",
                "exit_code": 0,
                "duration_ms": 111,
                "run": {"run_id": "old-run", "run_attempt": "1"},
            },
            {
                "name": "current step",
                "exit_code": 0,
                "duration_ms": 222,
                "run": {"run_id": "new-run", "run_attempt": "2"},
            },
        ],
    )

    assert summarize(metrics_dir, public, out, None) == 0

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert [step["name"] for step in payload["steps"]] == ["current step"]
    assert payload["run"] == {"run_id": "new-run", "run_attempt": "2"}
    assert payload["warnings"] == [
        "Ignored 1 stale build metric step row(s) because they do not match "
        "GITHUB_RUN_ID=new-run GITHUB_RUN_ATTEMPT=2."
    ]
