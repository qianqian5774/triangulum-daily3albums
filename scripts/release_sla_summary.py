#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone as datetime_timezone
from pathlib import Path


DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_TARGET_TIME = "08:00"
BJT = datetime_timezone(timedelta(hours=8), name=DEFAULT_TIMEZONE)


@dataclass(frozen=True)
class ReleaseSla:
    status: str
    timezone: str
    target_unlock: str
    build_started_at: str
    deploy_finished_at: str
    deploy_outcome: str
    event_name: str
    duration_seconds: int
    margin_seconds: int


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include a timezone offset: {value}")
    return parsed


def _parse_target_time(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"target time must use HH:MM or HH:MM:SS: {value}") from exc


def evaluate_release_sla(
    started_at: str,
    finished_at: str,
    *,
    timezone: str = DEFAULT_TIMEZONE,
    target_time: str = DEFAULT_TARGET_TIME,
    deploy_outcome: str = "success",
    event_name: str = "schedule",
) -> ReleaseSla:
    if timezone != DEFAULT_TIMEZONE:
        raise ValueError(f"unsupported product timezone: {timezone}")
    tz = BJT
    started = _parse_datetime(started_at)
    finished = _parse_datetime(finished_at)
    if finished < started:
        raise ValueError("deploy finish cannot be earlier than build start")
    finished_local = finished.astimezone(tz)
    target_local = datetime.combine(
        finished_local.date(),
        _parse_target_time(target_time),
        tzinfo=tz,
    )
    margin_seconds = int((target_local - finished_local).total_seconds())
    normalized_outcome = deploy_outcome.strip().lower() or "unknown"
    normalized_event = event_name.strip().lower() or "unknown"
    if normalized_outcome != "success":
        status = "deploy_failed"
    elif normalized_event != "schedule":
        status = "observed"
    else:
        status = "on_time" if margin_seconds >= 0 else "late"
    return ReleaseSla(
        status=status,
        timezone=timezone,
        target_unlock=target_local.isoformat(timespec="seconds"),
        build_started_at=started.astimezone(tz).isoformat(timespec="seconds"),
        deploy_finished_at=finished_local.isoformat(timespec="seconds"),
        deploy_outcome=normalized_outcome,
        event_name=normalized_event,
        duration_seconds=int((finished - started).total_seconds()),
        margin_seconds=margin_seconds,
    )


def _format_signed_minutes(seconds: int) -> str:
    minutes = abs(seconds) // 60
    if seconds >= 0:
        return f"{minutes} minutes before target"
    return f"{minutes} minutes after target"


def render_markdown(result: ReleaseSla) -> str:
    return "\n".join(
        [
            "## Daily release SLA",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Status | `{result.status}` |",
            f"| Build started | `{result.build_started_at}` |",
            f"| Deploy finished | `{result.deploy_finished_at}` |",
            f"| Target unlock | `{result.target_unlock}` |",
            f"| Deploy outcome | `{result.deploy_outcome}` |",
            f"| Trigger | `{result.event_name}` |",
            f"| Build-to-deploy duration | `{result.duration_seconds} seconds` |",
            f"| Target margin | `{_format_signed_minutes(result.margin_seconds)}` |",
            "",
        ]
    )


def _append_summary(markdown: str, explicit_path: str | None) -> None:
    raw = explicit_path or os.getenv("GITHUB_STEP_SUMMARY", "").strip()
    if not raw:
        return
    path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize the daily 08:00 BJT release SLA.")
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--finished-at", default="")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument("--target-time", default=DEFAULT_TARGET_TIME)
    parser.add_argument("--deploy-outcome", default="success")
    parser.add_argument("--event-name", default="schedule")
    parser.add_argument("--github-summary", action="store_true")
    parser.add_argument("--summary-file", default="")
    args = parser.parse_args(argv)

    finished_at = args.finished_at or datetime.now().astimezone().isoformat(timespec="seconds")
    result = evaluate_release_sla(
        args.started_at,
        finished_at,
        timezone=args.timezone,
        target_time=args.target_time,
        deploy_outcome=args.deploy_outcome,
        event_name=args.event_name,
    )
    markdown = render_markdown(result)
    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    print(markdown)
    if args.github_summary or args.summary_file:
        _append_summary(markdown, args.summary_file or None)
    if result.status == "late":
        late_minutes = abs(result.margin_seconds) // 60
        print(
            f"::warning title=Daily release SLA missed::Deployment finished "
            f"{late_minutes} minutes after the 08:00 BJT target"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
