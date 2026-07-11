from __future__ import annotations

from scripts.release_sla_summary import evaluate_release_sla, main, render_markdown


def test_release_sla_reports_positive_margin_before_0800():
    result = evaluate_release_sla(
        "2026-07-11T06:10:00+08:00",
        "2026-07-11T06:20:00+08:00",
    )
    assert result.status == "on_time"
    assert result.duration_seconds == 600
    assert result.margin_seconds == 100 * 60
    assert "100 minutes before target" in render_markdown(result)


def test_release_sla_reports_late_deploy_and_emits_warning(capsys):
    rc = main(
        [
            "--started-at",
            "2026-07-11T07:50:00+08:00",
            "--finished-at",
            "2026-07-11T08:05:00+08:00",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert '"status": "late"' in output
    assert "::warning title=Daily release SLA missed::" in output
    assert "5 minutes after" in output


def test_release_sla_normalizes_utc_timestamps_to_bjt():
    result = evaluate_release_sla(
        "2026-07-10T22:10:00Z",
        "2026-07-10T22:20:00Z",
    )
    assert result.build_started_at == "2026-07-11T06:10:00+08:00"
    assert result.deploy_finished_at == "2026-07-11T06:20:00+08:00"
    assert result.target_unlock == "2026-07-11T08:00:00+08:00"


def test_release_sla_keeps_deploy_failure_distinct_from_lateness():
    result = evaluate_release_sla(
        "2026-07-11T06:10:00+08:00",
        "2026-07-11T06:20:00+08:00",
        deploy_outcome="failure",
    )
    assert result.status == "deploy_failed"


def test_manual_run_records_margin_without_false_sla_warning(capsys):
    rc = main(
        [
            "--started-at",
            "2026-07-11T19:50:00+08:00",
            "--finished-at",
            "2026-07-11T20:05:00+08:00",
            "--event-name",
            "workflow_dispatch",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert '"status": "observed"' in output
    assert "::warning" not in output
