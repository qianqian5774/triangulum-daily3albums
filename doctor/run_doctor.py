from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional
from urllib.parse import urlsplit

import yaml

from daily3albums.adapters import lastfm_tag_top_albums, musicbrainz_search_release_group
from daily3albums.config import load_config, load_env
from daily3albums.request_broker import RequestBroker


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class StepResult:
    id: str
    name: str
    exit_code: int
    duration_ms: int
    log_path: str
    artifacts: list[str]


@dataclass
class Issue:
    severity: str
    what: str
    where: str
    repro: str
    fix: str
    risk: str
    rollback: str
    verify: str
    evidence_paths: list[str]


@dataclass
class RenderAudit:
    target_id: str
    viewport: str
    url: str
    json_path: str
    svg_path: str
    fingerprint: str


@dataclass
class RunContext:
    run_id: str
    started_at: str
    commit: str
    env: dict[str, str]
    plan: dict[str, Any]
    logs_dir: Path
    artifacts_dir: Path
    ui_audit_dir: Path
    fixed_report_md: Path
    fixed_report_json: Path
    fixed_screenshots: dict[str, Path]
    latest_dir: Path
    sanitization_notes: list[str]
    build_command: list[str]
    issues: list[Issue]
    steps: list[StepResult]
    checks: dict[str, Any]
    overall_status: str


FALLBACK_PLAN = {
    "doctor_plan": {
        "version": 1,
        "name": "fallback_plan",
        "fixed_paths": {
            "report_md": "doctor/REPORT.md",
            "report_json": "doctor/REPORT.json",
            "screenshots": {
                "today": "doctor/screenshots/today.svg",
                "archive": "doctor/screenshots/archive.svg",
                "detail": "doctor/screenshots/detail.svg",
            },
            "latest_run_dir": "doctor/runs/latest",
        },
        "per_run_layout": {
            "root": "doctor/runs/{run_id}",
            "logs_dir": "doctor/runs/{run_id}/logs",
            "artifacts_dir": "doctor/runs/{run_id}/artifacts",
            "ui_audit_dir": "doctor/runs/{run_id}/ui_audit",
        },
        "hard_gates": [],
        "viewports": {
            "desktop": {"width": 1280, "height": 720},
            "mobile": {"width": 375, "height": 812},
        },
        "ui_targets": [
            {"id": "today", "label": "Today", "primary_url_path": "/"},
            {"id": "archive", "label": "Archive", "primary_url_path": "/archive.html"},
            {"id": "detail", "label": "Detail", "primary_url_path": "/"},
        ],
        "steps": [],
    }
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT)
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_text(path: Path, text: str) -> None:
    _ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def _sanitize_yaml_block(yaml_text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    sanitized_lines: list[str] = []
    for line in yaml_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("name:") or stripped.startswith("label:"):
            key, _, value = stripped.partition(":")
            value = value.strip()
            if value.startswith(("'", '"')):
                sanitized_lines.append(line)
                continue
            if ": " in value:
                escaped = value.replace('"', '\\"')
                new_value = f'"{escaped}"'
                prefix = line[: len(line) - len(stripped)]
                sanitized_lines.append(f"{prefix}{key}: {new_value}")
                notes.append(f"sanitized {key}: {value} -> {new_value}")
                continue
        sanitized_lines.append(line)
    return "\n".join(sanitized_lines), notes


def _extract_plan_yaml(agents_text: str) -> tuple[str, list[str]]:
    match = re.search(r"```yaml(.*?)```", agents_text, re.DOTALL)
    if not match:
        raise ValueError("doctor_plan YAML block not found in AGENTS.md")
    raw_yaml = match.group(1).strip()
    sanitized_yaml, notes = _sanitize_yaml_block(raw_yaml)
    return sanitized_yaml, notes


def _load_plan() -> tuple[dict[str, Any], list[str], Optional[str]]:
    agents_path = REPO_ROOT / "AGENTS.md"
    if not agents_path.exists():
        return FALLBACK_PLAN, [], "AGENTS.md missing"
    try:
        agents_text = agents_path.read_text(encoding="utf-8")
    except Exception as exc:
        return FALLBACK_PLAN, [], f"Failed to read AGENTS.md: {exc}"
    try:
        yaml_text, notes = _extract_plan_yaml(agents_text)
        plan = yaml.safe_load(yaml_text)
        if not isinstance(plan, dict) or "doctor_plan" not in plan:
            raise ValueError("doctor_plan key missing after parse")
        return plan, notes, None
    except Exception as exc:
        return FALLBACK_PLAN, [], f"Failed to parse doctor_plan YAML: {exc}"


def _placeholder_svg(
    *,
    width: int,
    height: int,
    title: str,
    reason: str,
    url: str,
    run_id: str,
    commit: str,
    timestamp: str,
    evidence: Iterable[str],
) -> str:
    evidence_text = "\\n".join(evidence)
    escaped_reason = _xml_escape(reason)
    escaped_url = _xml_escape(url)
    escaped_title = _xml_escape(title)
    escaped_evidence = _xml_escape(evidence_text)
    return textwrap.dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
          <rect width="100%" height="100%" fill="#0b0b0f"/>
          <text x="32" y="48" fill="#e8e8f0" font-family="monospace" font-size="20">{escaped_title}</text>
          <text x="32" y="80" fill="#c3c3d0" font-family="monospace" font-size="14">reason: {escaped_reason}</text>
          <text x="32" y="104" fill="#c3c3d0" font-family="monospace" font-size="14">url: {escaped_url}</text>
          <text x="32" y="128" fill="#c3c3d0" font-family="monospace" font-size="14">run_id: {run_id}</text>
          <text x="32" y="152" fill="#c3c3d0" font-family="monospace" font-size="14">commit: {commit}</text>
          <text x="32" y="176" fill="#c3c3d0" font-family="monospace" font-size="14">timestamp: {timestamp}</text>
          <text x="32" y="212" fill="#9ea0b3" font-family="monospace" font-size="12">evidence:</text>
          <text x="32" y="232" fill="#9ea0b3" font-family="monospace" font-size="12">{escaped_evidence}</text>
        </svg>
        """
    )


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _write_placeholder_set(ctx: RunContext, reason: str) -> dict[str, str]:
    viewports = ctx.plan["doctor_plan"]["viewports"]
    width = int(viewports.get("desktop", {}).get("width", 1280))
    height = int(viewports.get("desktop", {}).get("height", 720))
    outputs: dict[str, str] = {}
    for key, path in ctx.fixed_screenshots.items():
        svg = _placeholder_svg(
            width=width,
            height=height,
            title=f"{key} (placeholder)",
            reason=reason,
            url="",
            run_id=ctx.run_id,
            commit=ctx.commit,
            timestamp=ctx.started_at,
            evidence=[str(ctx.logs_dir / "render_qa.log")],
        )
        _write_text(path, svg)
        outputs[key] = str(path)
    return outputs


def _run_step(
    ctx: RunContext,
    step_id: str,
    name: str,
    func: Callable[[RunContext, Callable[[str], None]], tuple[int, list[str]]],
) -> StepResult:
    log_path = ctx.logs_dir / f"{step_id}.log"
    log_lines: list[str] = []

    def logger(msg: str) -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        log_lines.append(f"[{stamp}] {msg}")

    start = time.monotonic()
    exit_code, artifacts = func(ctx, logger)
    duration_ms = int((time.monotonic() - start) * 1000)
    _write_text(log_path, "\n".join(log_lines))
    result = StepResult(
        id=step_id,
        name=name,
        exit_code=exit_code,
        duration_ms=duration_ms,
        log_path=str(log_path),
        artifacts=artifacts,
    )
    ctx.steps.append(result)
    return result


def _overview_discovery(ctx: RunContext, logger: Callable[[str], None]) -> tuple[int, list[str]]:
    artifacts: list[str] = []
    cfg = load_config(REPO_ROOT)
    tag = "electronic"
    theme_items = cfg.raw.get("themes", {}).get("items", [])
    if theme_items:
        first = theme_items[0]
        tags = first.get("seed_tags") or []
        if tags:
            tag = tags[0]
    build_cmd = [sys.executable, "-m", "daily3albums.cli", "build", "--tag", tag, "--verbose"]
    ctx.build_command = build_cmd
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    logger("Discovered README build instruction: daily3albums build --tag <tag> --verbose")
    logger("Doctor will invoke build via: python -m daily3albums.cli build")
    logger(f"Selected build tag: {tag}")
    ctx.checks.setdefault("discovery", {})
    ctx.checks["discovery"].update(
        {
            "build_command": build_cmd,
            "timezone": cfg.timezone,
            "readme_snippet": readme.splitlines()[:12],
        }
    )
    artifacts.append("README.md")
    return 0, artifacts


def _config_check(ctx: RunContext, logger: Callable[[str], None]) -> tuple[int, list[str]]:
    env = load_env(REPO_ROOT)
    ok = True
    missing: list[str] = []
    if not env.lastfm_api_key:
        ok = False
        missing.append("LASTFM_API_KEY")
    if not env.mb_user_agent:
        ok = False
        missing.append("MB_USER_AGENT")
    ctx.checks.setdefault("config", {})
    ctx.checks["config"].update(
        {
            "lastfm_configured": bool(env.lastfm_api_key),
            "musicbrainz_configured": bool(env.mb_user_agent),
            "missing": missing,
        }
    )
    if not ok:
        ctx.issues.append(
            Issue(
                severity="high",
                what="Missing external API configuration",
                where="config_check",
                repro="Run python -m doctor.run_doctor without required environment variables.",
                fix="Set LASTFM_API_KEY and MB_USER_AGENT in the environment or .env file.",
                risk="External probes and build will fail; output will be stale.",
                rollback="Use cached data and skip probes.",
                verify="Re-run doctor; config check should pass.",
                evidence_paths=[str(ctx.logs_dir / "config_check.log")],
            )
        )
    logger(f"Config missing: {missing}" if missing else "Config OK")
    return (0 if ok else 1), []


def _probe_lastfm(ctx: RunContext, logger: Callable[[str], None]) -> tuple[int, list[str]]:
    env = load_env(REPO_ROOT)
    cfg = load_config(REPO_ROOT)
    if not env.lastfm_api_key:
        logger("Last.fm API key missing; skipping probe.")
        return 1, []
    tag = ctx.build_command[3] if ctx.build_command else "electronic"
    broker = RequestBroker(repo_root=REPO_ROOT, endpoint_policies=cfg.policies, logger=logger)
    try:
        albums = lastfm_tag_top_albums(broker, api_key=env.lastfm_api_key, tag=tag, limit=1)
        ctx.checks.setdefault("probes", {})
        ctx.checks["probes"]["lastfm"] = {"ok": bool(albums), "count": len(albums)}
        if not albums:
            raise RuntimeError("No albums returned from Last.fm")
        return 0, []
    except Exception as exc:
        ctx.issues.append(
            Issue(
                severity="high",
                what="Last.fm minimal probe failed",
                where="probe_lastfm_minimal",
                repro=f"Run probe-lastfm with tag {tag}",
                fix="Verify API key and endpoint policies; ensure cache allows Last.fm.",
                risk="Build cannot fetch top albums.",
                rollback="Use cached data or fixtures for probes.",
                verify="Re-run probe_lastfm_minimal and confirm success.",
                evidence_paths=[str(ctx.logs_dir / "probe_lastfm.log")],
            )
        )
        logger(f"Last.fm probe error: {exc}")
        return 1, []
    finally:
        broker.close()


def _probe_musicbrainz(ctx: RunContext, logger: Callable[[str], None]) -> tuple[int, list[str]]:
    env = load_env(REPO_ROOT)
    cfg = load_config(REPO_ROOT)
    if not env.mb_user_agent:
        logger("MusicBrainz user agent missing; skipping probe.")
        return 1, []
    broker = RequestBroker(repo_root=REPO_ROOT, endpoint_policies=cfg.policies, logger=logger)
    try:
        rgs = musicbrainz_search_release_group(
            broker,
            mb_user_agent=env.mb_user_agent,
            artist="Aphex Twin",
            title="Selected Ambient Works",
            limit=1,
        )
        ctx.checks.setdefault("probes", {})
        ctx.checks["probes"]["musicbrainz"] = {"ok": bool(rgs), "count": len(rgs)}
        if not rgs:
            raise RuntimeError("No release groups returned from MusicBrainz")
        return 0, []
    except Exception as exc:
        ctx.issues.append(
            Issue(
                severity="high",
                what="MusicBrainz minimal probe failed",
                where="probe_musicbrainz_minimal",
                repro="Run probe-mb with artist/title inputs.",
                fix="Verify MB_USER_AGENT and endpoint policies; ensure cache allows MusicBrainz.",
                risk="Build cannot normalize releases.",
                rollback="Use cached data or fixtures for probes.",
                verify="Re-run probe_musicbrainz_minimal and confirm success.",
                evidence_paths=[str(ctx.logs_dir / "probe_musicbrainz.log")],
            )
        )
        logger(f"MusicBrainz probe error: {exc}")
        return 1, []
    finally:
        broker.close()


def _soft_probes(ctx: RunContext, logger: Callable[[str], None]) -> tuple[int, list[str]]:
    env = load_env(REPO_ROOT)
    ctx.checks.setdefault("probes", {})
    ctx.checks["probes"]["soft"] = {
        "discogs_token": bool(env.discogs_token),
        "listenbrainz_token": bool(env.listenbrainz_token),
        "openai_api_key": bool(env.openai_api_key),
    }
    logger("Soft probes recorded (tokens presence only).")
    return 0, []


def _build_public(ctx: RunContext, logger: Callable[[str], None]) -> tuple[int, list[str]]:
    cmd = ctx.build_command or ["daily3albums", "build", "--tag", "electronic", "--verbose"]
    logger(f"Running build: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    log_path = ctx.logs_dir / "build_public.command.log"
    _write_text(log_path, proc.stdout + "\n" + proc.stderr)
    artifacts: list[str] = []
    out_dir = REPO_ROOT / "_build" / "public"
    if out_dir.exists():
        artifacts.append(str(out_dir))
    if proc.returncode != 0:
        ctx.issues.append(
            Issue(
                severity="high",
                what="Build step failed",
                where="build_public",
                repro=f"Run {' '.join(cmd)}",
                fix="Install Node.js/npm and ensure API keys are configured.",
                risk="Static site and JSON artifacts are missing.",
                rollback="Use last known good build artifacts.",
                verify="Re-run build and confirm _build/public exists.",
                evidence_paths=[str(log_path)],
            )
        )
    return proc.returncode, artifacts


def _validate_artifacts(ctx: RunContext, logger: Callable[[str], None]) -> tuple[int, list[str]]:
    data_dir = REPO_ROOT / "_build" / "public" / "data"
    today_path = data_dir / "today.json"
    artifacts: list[str] = []
    if not today_path.exists():
        ctx.issues.append(
            Issue(
                severity="high",
                what="today.json missing",
                where="validate_artifacts",
                repro="Run build to generate _build/public/data/today.json.",
                fix="Ensure build succeeds and writes data artifacts.",
                risk="UI has no content to render.",
                rollback="Use cached artifacts from previous run.",
                verify="Confirm today.json exists and contains 3 picks.",
                evidence_paths=[str(today_path)],
            )
        )
        return 1, artifacts
    artifacts.append(str(today_path))
    try:
        today = json.loads(today_path.read_text(encoding="utf-8"))
    except Exception as exc:
        ctx.issues.append(
            Issue(
                severity="high",
                what="today.json unreadable",
                where="validate_artifacts",
                repro="Open today.json",
                fix="Inspect data generation pipeline and fix JSON serialization.",
                risk="UI may crash on load.",
                rollback="Restore last known good today.json.",
                verify="Confirm today.json is valid JSON.",
                evidence_paths=[str(today_path)],
            )
        )
        logger(f"today.json parse error: {exc}")
        return 1, artifacts
    picks = today.get("picks", [])
    ctx.checks.setdefault("artifacts", {})
    ctx.checks["artifacts"]["today_pick_count"] = len(picks)
    if len(picks) != 3:
        ctx.issues.append(
            Issue(
                severity="medium",
                what="today.json does not contain 3 picks",
                where="validate_artifacts",
                repro="Inspect today.json picks array length.",
                fix="Ensure build pipeline emits three slots.",
                risk="UI layout may be incomplete.",
                rollback="Re-run build or restore cached artifacts.",
                verify="Confirm today.json has three picks.",
                evidence_paths=[str(today_path)],
            )
        )
        return 1, artifacts
    logger("Artifacts validated (today.json).")
    return 0, artifacts


def _render_qa(ctx: RunContext, logger: Callable[[str], None]) -> tuple[int, list[str]]:
    viewports = ctx.plan["doctor_plan"].get("viewports", {})
    ui_targets = ctx.plan["doctor_plan"].get("ui_targets", [])
    artifacts: list[str] = []
    out_dir = REPO_ROOT / "_build" / "public"
    if not out_dir.exists():
        reason = "_build/public missing; cannot run render QA."
        logger(reason)
        _write_placeholder_set(ctx, reason)
        return 1, []
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        reason = f"Playwright unavailable: {exc}"
        logger(reason)
        _write_placeholder_set(ctx, reason)
        return 1, []

    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8000", "--directory", str(out_dir)],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = "http://127.0.0.1:8000"
    audits: list[RenderAudit] = []
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:
                reason = f"Playwright launch failed: {exc}"
                logger(reason)
                _write_placeholder_set(ctx, reason)
                ctx.issues.append(
                    Issue(
                        severity="high",
                        what="Render QA failed to launch Playwright browser",
                        where="render_qa",
                        repro="Run playwright install then re-run doctor.",
                        fix="Install Playwright browsers or configure playwright install in the environment.",
                        risk="UI render QA evidence missing.",
                        rollback="Use placeholder SVGs and skip render QA.",
                        verify="Re-run render QA and confirm SVGs are generated.",
                        evidence_paths=[str(ctx.logs_dir / "render_qa.log")],
                    )
                )
                return 1, []
            for target in ui_targets:
                target_id = target.get("id")
                target_url = _resolve_target_url(base_url, target, logger, browser)
                for viewport_name, vp in viewports.items():
                    page = browser.new_page(viewport={"width": int(vp["width"]), "height": int(vp["height"])})
                    render_info = _capture_render_audit(
                        page=page,
                        target_id=target_id,
                        url=target_url,
                        viewport=viewport_name,
                        ctx=ctx,
                        logger=logger,
                    )
                    audits.append(render_info)
                    artifacts.extend([render_info.json_path, render_info.svg_path])
                    page.close()
            browser.close()
    except Exception as exc:
        reason = f"Render QA failed: {exc}"
        logger(reason)
        _write_placeholder_set(ctx, reason)
        ctx.issues.append(
            Issue(
                severity="high",
                what="Render QA encountered an error",
                where="render_qa",
                repro="Run python -m doctor.run_doctor and observe render QA logs.",
                fix="Inspect logs for Playwright/server errors and resolve them.",
                risk="UI render QA evidence missing.",
                rollback="Use placeholder SVGs and skip render QA.",
                verify="Re-run render QA and confirm SVGs are generated.",
                evidence_paths=[str(ctx.logs_dir / "render_qa.log")],
            )
        )
        return 1, []
    finally:
        server.terminate()
        server.wait(timeout=5)

    ctx.checks.setdefault("render_qa", {})
    ctx.checks["render_qa"]["audits"] = [dataclasses.asdict(a) for a in audits]
    ctx.checks.setdefault("artifacts", {})
    ctx.checks["artifacts"]["fingerprints"] = {
        f"{a.target_id}.{a.viewport}": a.fingerprint for a in audits
    }
    _sync_latest_screenshots(ctx, audits)
    return 0, artifacts


def _resolve_target_url(base_url: str, target: dict[str, Any], logger: Callable[[str], None], browser: Any) -> str:
    path = target.get("primary_url_path") or "/"
    if target.get("id") == "archive":
        return base_url + path
    if target.get("id") == "detail":
        return base_url + "/"
    if target.get("discovery") == "nav_link_contains":
        try:
            page = browser.new_page()
            page.goto(base_url + "/", wait_until="networkidle")
            match_sub = target.get("match_substring", "archive")
            href = page.evaluate(
                """(matchSub) => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const target = links.find((link) => (link.getAttribute('href') || '').includes(matchSub));
                    return target ? target.getAttribute('href') : null;
                }""",
                match_sub,
            )
            page.close()
            if href:
                return base_url + href
        except Exception as exc:
            logger(f"Archive discovery failed: {exc}")
        fallback_paths = target.get("fallback_paths") or ["/archive", "/archive.html"]
        return base_url + fallback_paths[0]
    return base_url + path


def _capture_render_audit(
    *,
    page: Any,
    target_id: str,
    url: str,
    viewport: str,
    ctx: RunContext,
    logger: Callable[[str], None],
) -> RenderAudit:
    console_entries: list[dict[str, str]] = []
    page_errors: list[str] = []
    request_log: list[dict[str, Any]] = []
    request_start: dict[str, float] = {}

    def on_console(msg: Any) -> None:
        console_entries.append({"type": msg.type, "text": msg.text})

    def on_page_error(err: Any) -> None:
        page_errors.append(str(err))

    def on_request(req: Any) -> None:
        request_start[req.url] = time.monotonic()

    def on_request_finished(req: Any) -> None:
        response = req.response()
        duration_ms = int((time.monotonic() - request_start.get(req.url, time.monotonic())) * 1000)
        request_log.append(
            {
                "url": req.url,
                "status": response.status if response else None,
                "resource_type": req.resource_type,
                "duration_ms": duration_ms,
            }
        )

    def on_request_failed(req: Any) -> None:
        duration_ms = int((time.monotonic() - request_start.get(req.url, time.monotonic())) * 1000)
        request_log.append(
            {
                "url": req.url,
                "status": None,
                "resource_type": req.resource_type,
                "duration_ms": duration_ms,
                "failed": True,
                "failure": req.failure,
            }
        )

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("request", on_request)
    page.on("requestfinished", on_request_finished)
    page.on("requestfailed", on_request_failed)

    page.goto(url, wait_until="networkidle")
    origin = _origin_from_url(url)

    if target_id == "detail":
        try:
            page.click('[data-testid="album-card-0"]')
            page.wait_for_timeout(500)
        except Exception as exc:
            logger(f"Detail overlay click failed: {exc}")

    data_consistency = {}
    if target_id == "today":
        data_consistency = _compare_today_data(page, ctx, logger)

    overflow = page.evaluate(
        """() => {
            const doc = document.documentElement;
            return {
              scrollWidth: doc.scrollWidth,
              clientWidth: doc.clientWidth,
              overflow: doc.scrollWidth > doc.clientWidth,
              delta: doc.scrollWidth - doc.clientWidth
            };
        }"""
    )
    visibility = page.evaluate(
        """() => {
            const main = document.querySelector('main') || document.body;
            if (!main) return {visible: false};
            const style = window.getComputedStyle(main);
            const rect = main.getBoundingClientRect();
            return {
              visible: !(style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0'),
              height: rect.height,
              width: rect.width
            };
        }"""
    )
    a11y = page.evaluate(
        """() => {
            const imgs = Array.from(document.querySelectorAll('img'));
            const missingAlt = imgs.filter((img) => !img.getAttribute('alt'));
            const html = document.documentElement;
            const hasLang = !!html.getAttribute('lang');
            return {
              missing_alt_count: missingAlt.length,
              total_images: imgs.length,
              html_lang_present: hasLang
            };
        }"""
    )
    internal_links = _check_internal_links(page, origin, logger)
    dom_snapshot = _dom_to_svg(page, url, viewport, ctx, logger)
    svg_path = ctx.ui_audit_dir / f"{target_id}.{viewport}.svg"
    _write_text(svg_path, dom_snapshot["svg"])
    json_path = ctx.ui_audit_dir / f"{target_id}.{viewport}.json"
    external_requests = [req for req in request_log if not req["url"].startswith(origin)]
    audit_payload = {
        "target_id": target_id,
        "viewport": viewport,
        "url": url,
        "console": console_entries,
        "page_errors": page_errors,
        "network": request_log,
        "external_requests": external_requests,
        "internal_links": internal_links,
        "data_consistency": data_consistency,
        "overflow": overflow,
        "visibility": visibility,
        "a11y": a11y,
        "dom_snapshot": {k: v for k, v in dom_snapshot.items() if k != "svg"},
    }
    _write_text(json_path, json.dumps(audit_payload, indent=2))
    fingerprint = hashlib.sha256(
        (dom_snapshot["text_hash"] + json.dumps(audit_payload, sort_keys=True)).encode("utf-8")
    ).hexdigest()
    _maybe_report_render_issues(ctx, audit_payload, str(json_path))
    return RenderAudit(
        target_id=target_id,
        viewport=viewport,
        url=url,
        json_path=str(json_path),
        svg_path=str(svg_path),
        fingerprint=fingerprint,
    )


def _dom_to_svg(page: Any, url: str, viewport: str, ctx: RunContext, logger: Callable[[str], None]) -> dict[str, str]:
    try:
        payload = page.evaluate(
            """() => {
                const html = document.documentElement.outerHTML;
                const styles = [];
                const errors = [];
                for (const sheet of Array.from(document.styleSheets)) {
                  try {
                    const rules = Array.from(sheet.cssRules || []).map((r) => r.cssText).join("\\n");
                    styles.push(rules);
                  } catch (err) {
                    errors.push(String(err));
                  }
                }
                return { html, styles: styles.join("\\n"), errors };
            }"""
        )
        width = page.viewport_size["width"]
        height = page.viewport_size["height"]
        html = payload["html"]
        styles = payload["styles"]
        errors = payload["errors"]
        if errors:
            logger(f"Stylesheet access errors: {errors}")
        svg = textwrap.dedent(
            f"""\
            <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
              <foreignObject width="100%" height="100%">
                <style><![CDATA[{styles}]]></style>
                {html}
              </foreignObject>
            </svg>
            """
        )
        return {
            "svg": svg,
            "url": url,
            "viewport": viewport,
            "stylesheet_errors": errors,
            "text_hash": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        }
    except Exception as exc:
        reason = f"DOM snapshot failed: {exc}"
        logger(reason)
        width = page.viewport_size["width"]
        height = page.viewport_size["height"]
        svg = _placeholder_svg(
            width=width,
            height=height,
            title=f"{url} ({viewport})",
            reason=reason,
            url=url,
            run_id=ctx.run_id,
            commit=ctx.commit,
            timestamp=ctx.started_at,
            evidence=[str(ctx.logs_dir / "render_qa.log")],
        )
        return {
            "svg": svg,
            "url": url,
            "viewport": viewport,
            "stylesheet_errors": [reason],
            "text_hash": hashlib.sha256(reason.encode("utf-8")).hexdigest(),
        }


def _maybe_report_render_issues(ctx: RunContext, audit: dict[str, Any], json_path: str) -> None:
    errors = [e for e in audit.get("console", []) if e.get("type") in {"error", "warning"}]
    if errors or audit.get("page_errors"):
        ctx.issues.append(
            Issue(
                severity="medium",
                what="Console warnings/errors detected during render",
                where=audit["url"],
                repro=f"Open {audit['url']} and inspect console",
                fix="Investigate logged console warnings/errors and address root cause.",
                risk="User-facing errors or missing UI elements.",
                rollback="Disable recent UI changes or revert assets.",
                verify="Reload page and ensure console is clean.",
                evidence_paths=[json_path],
            )
        )
    network_failures = [r for r in audit.get("network", []) if r.get("status") in {404, 500} or r.get("failed")]
    if network_failures:
        ctx.issues.append(
            Issue(
                severity="medium",
                what="Network failures during render",
                where=audit["url"],
                repro="Load the page and inspect network tab for failed resources.",
                fix="Restore missing assets or update references.",
                risk="Broken styles, missing data, or blank pages.",
                rollback="Revert asset pipeline changes.",
                verify="Confirm all network requests succeed.",
                evidence_paths=[json_path],
            )
        )
    if audit.get("overflow", {}).get("overflow"):
        ctx.issues.append(
            Issue(
                severity="low",
                what="Horizontal overflow detected",
                where=audit["url"],
                repro="Open page and check for horizontal scroll.",
                fix="Adjust layout to prevent overflow on viewport.",
                risk="Layout clipped or requires scrolling.",
                rollback="Undo recent CSS changes.",
                verify="Confirm scrollWidth equals clientWidth.",
                evidence_paths=[json_path],
            )
        )
    a11y = audit.get("a11y", {})
    if a11y.get("missing_alt_count", 0) > 0 or not a11y.get("html_lang_present", True):
        ctx.issues.append(
            Issue(
                severity="low",
                what="Accessibility smoke check warnings",
                where=audit["url"],
                repro="Inspect DOM for missing alt or lang attributes.",
                fix="Add alt text and document language attributes.",
                risk="Screen reader users may lose context.",
                rollback="Revert markup changes.",
                verify="Re-run render QA and confirm a11y checks pass.",
                evidence_paths=[json_path],
            )
        )
    external_requests = audit.get("external_requests", [])
    if external_requests:
        ctx.issues.append(
            Issue(
                severity="medium",
                what="External network requests during render",
                where=audit["url"],
                repro="Load page and inspect network requests to external domains.",
                fix="Bundle assets locally or remove external dependencies.",
                risk="Static site depends on external availability.",
                rollback="Revert to locally hosted assets.",
                verify="Re-run render QA and confirm no external requests.",
                evidence_paths=[json_path],
            )
        )
    broken_links = [l for l in audit.get("internal_links", []) if l.get("status") not in {200, 301, 302}]
    if broken_links:
        ctx.issues.append(
            Issue(
                severity="low",
                what="Internal link checks failed",
                where=audit["url"],
                repro="Click internal links and observe 404 responses.",
                fix="Update links or ensure referenced pages exist.",
                risk="Navigation failures for users.",
                rollback="Restore previous links.",
                verify="Re-run render QA and confirm links return 200.",
                evidence_paths=[json_path],
            )
        )


def _origin_from_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _check_internal_links(page: Any, origin: str, logger: Callable[[str], None]) -> list[dict[str, Any]]:
    links = page.evaluate(
        """() => Array.from(document.querySelectorAll('a'))
          .map((link) => link.getAttribute('href'))
          .filter((href) => href && !href.startsWith('http') && !href.startsWith('mailto:'))"""
    )
    results: list[dict[str, Any]] = []
    for href in links[:5]:
        url = origin + href
        try:
            response = page.request.get(url)
            results.append({"href": href, "status": response.status})
        except Exception as exc:
            logger(f"Internal link check failed for {href}: {exc}")
            results.append({"href": href, "status": None, "error": str(exc)})
    return results


def _compare_today_data(page: Any, ctx: RunContext, logger: Callable[[str], None]) -> dict[str, Any]:
    today_path = REPO_ROOT / "_build" / "public" / "data" / "today.json"
    if not today_path.exists():
        return {"status": "missing_data"}
    try:
        today = json.loads(today_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger(f"today.json parse error: {exc}")
        return {"status": "invalid_data"}
    expected = [(pick.get("title"), pick.get("artist_credit")) for pick in today.get("picks", [])]
    ui_picks = page.evaluate(
        """() => Array.from(document.querySelectorAll('[data-testid^="album-card-"] h3'))
          .map((node) => node.textContent || '')
          .slice(0, 3)"""
    )
    matches = len(ui_picks) == len(expected) and all(
        expected[i] and expected[i][0] == ui_picks[i] for i in range(min(len(ui_picks), len(expected)))
    )
    result = {
        "status": "match" if matches else "mismatch",
        "expected_titles": [title for title, _ in expected],
        "ui_titles": ui_picks,
    }
    if not matches:
        ctx.issues.append(
            Issue(
                severity="medium",
                what="Today page data mismatch",
                where="render_qa",
                repro="Load the Today page and compare titles with data/today.json",
                fix="Ensure UI loads the correct data and renders all three picks.",
                risk="Users see incorrect or missing albums.",
                rollback="Revert UI data loading changes.",
                verify="Re-run render QA and compare titles.",
                evidence_paths=[str(today_path)],
            )
        )
    return result


def _sync_latest_screenshots(ctx: RunContext, audits: list[RenderAudit]) -> None:
    for key in ctx.fixed_screenshots:
        match = next((a for a in audits if a.target_id == key and a.viewport == "desktop"), None)
        if match:
            shutil.copy2(match.svg_path, ctx.fixed_screenshots[key])
        else:
            _write_text(
                ctx.fixed_screenshots[key],
                _placeholder_svg(
                    width=1280,
                    height=720,
                    title=f"{key} (missing)",
                    reason="Missing render audit output.",
                    url="",
                    run_id=ctx.run_id,
                    commit=ctx.commit,
                    timestamp=ctx.started_at,
                    evidence=[str(ctx.logs_dir / "render_qa.log")],
                ),
            )


def _finalize_reports(ctx: RunContext) -> None:
    report_md = _render_report_md(ctx)
    _write_text(ctx.fixed_report_md, report_md)
    report_json = {
        "meta": {
            "run_id": ctx.run_id,
            "timestamp": ctx.started_at,
            "commit": ctx.commit,
            "environment": ctx.env,
        },
        "overall_status": ctx.overall_status,
        "steps": [dataclasses.asdict(step) for step in ctx.steps],
        "checks": ctx.checks,
        "issues": [dataclasses.asdict(issue) for issue in ctx.issues],
    }
    _write_text(ctx.fixed_report_json, json.dumps(report_json, indent=2))


def _render_report_md(ctx: RunContext) -> str:
    steps_lines = "\n".join(
        f"- {step.id}: exit_code={step.exit_code} duration_ms={step.duration_ms} log={step.log_path}"
        for step in ctx.steps
    )
    issues_by_sev: dict[str, list[Issue]] = {}
    for issue in ctx.issues:
        issues_by_sev.setdefault(issue.severity, []).append(issue)
    issue_lines: list[str] = []
    for sev in sorted(issues_by_sev.keys()):
        issue_lines.append(f"### {sev}")
        for issue in issues_by_sev[sev]:
            issue_lines.append(
                textwrap.dedent(
                    f"""\
                    - what: {issue.what}
                      where: {issue.where}
                      repro: {issue.repro}
                      fix: {issue.fix}
                      risk: {issue.risk}
                      rollback: {issue.rollback}
                      verify: {issue.verify}
                      evidence: {", ".join(issue.evidence_paths)}
                    """
                ).strip()
            )
    issues_section = "\n".join(issue_lines) if issue_lines else "None"
    sanitization = "\n".join(ctx.sanitization_notes) if ctx.sanitization_notes else "None"
    render_audits = ctx.checks.get("render_qa", {}).get("audits", [])
    render_lines = "\n".join(
        f"- {a['target_id']} {a['viewport']}: {a['json_path']} svg={a['svg_path']}"
        for a in render_audits
    )
    report = textwrap.dedent(
        f"""\
        # Doctor Report

        ## Summary
        - environment: {ctx.env.get("python")}
        - commit: {ctx.commit}
        - run_id: {ctx.run_id}
        - overall_status: {ctx.overall_status}

        ## Steps
        {steps_lines}

        ## Findings
        - External probes: {json.dumps(ctx.checks.get("probes", {}))}
        - Build/artifacts validation: {json.dumps(ctx.checks.get("artifacts", {}))}
        - Screenshots index: {json.dumps({k: str(v) for k, v in ctx.fixed_screenshots.items()})}
        - Render QA summary:
        {render_lines or "None"}

        ## Issues
        {issues_section}

        ## Algorithm Trace
        - plan_source: AGENTS.md
        - sanitization: {sanitization}
        - run_parameters: build_command={ctx.build_command}
        - evidence_dirs: logs={ctx.logs_dir} ui_audit={ctx.ui_audit_dir} artifacts={ctx.artifacts_dir}

        ## Forward Risks & Coverage
        - steps_executed: {[step.id for step in ctx.steps]}
        - coverage_notes: If a step failed, downstream evidence may be placeholder-only.
        """
    )
    return report


def _ensure_fixed_paths(ctx: RunContext) -> None:
    _ensure_dir(ctx.fixed_report_md.parent)
    _ensure_dir(ctx.fixed_report_json.parent)
    _ensure_dir(ctx.fixed_screenshots["today"].parent)


def _copy_latest(ctx: RunContext) -> None:
    latest = ctx.latest_dir
    if latest.exists():
        if latest.is_symlink() or latest.is_file():
            latest.unlink()
        else:
            shutil.rmtree(latest)
    shutil.copytree(Path(ctx.logs_dir).parents[1], latest)


def run_doctor() -> int:
    plan, sanitization_notes, plan_error = _load_plan()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    started_at = _now_iso()
    commit = _git_commit()

    doctor_plan = plan["doctor_plan"]
    fixed_paths = doctor_plan["fixed_paths"]
    per_run_layout = doctor_plan["per_run_layout"]
    logs_dir = REPO_ROOT / per_run_layout["logs_dir"].format(run_id=run_id)
    artifacts_dir = REPO_ROOT / per_run_layout["artifacts_dir"].format(run_id=run_id)
    ui_audit_dir = REPO_ROOT / per_run_layout["ui_audit_dir"].format(run_id=run_id)
    latest_dir = REPO_ROOT / fixed_paths["latest_run_dir"]
    fixed_report_md = REPO_ROOT / fixed_paths["report_md"]
    fixed_report_json = REPO_ROOT / fixed_paths["report_json"]
    fixed_screenshots = {
        "today": REPO_ROOT / fixed_paths["screenshots"]["today"],
        "archive": REPO_ROOT / fixed_paths["screenshots"]["archive"],
        "detail": REPO_ROOT / fixed_paths["screenshots"]["detail"],
    }

    ctx = RunContext(
        run_id=run_id,
        started_at=started_at,
        commit=commit,
        env={"python": sys.version.split()[0]},
        plan=plan,
        logs_dir=logs_dir,
        artifacts_dir=artifacts_dir,
        ui_audit_dir=ui_audit_dir,
        fixed_report_md=fixed_report_md,
        fixed_report_json=fixed_report_json,
        fixed_screenshots=fixed_screenshots,
        latest_dir=latest_dir,
        sanitization_notes=sanitization_notes,
        build_command=[],
        issues=[],
        steps=[],
        checks={},
        overall_status="pass",
    )

    _ensure_dir(logs_dir)
    _ensure_dir(artifacts_dir)
    _ensure_dir(ui_audit_dir)
    _ensure_fixed_paths(ctx)
    if sanitization_notes:
        _write_text(logs_dir / "plan_sanitization.log", "\n".join(sanitization_notes))

    if plan_error:
        ctx.overall_status = "fail"
        ctx.issues.append(
            Issue(
                severity="high",
                what="Doctor plan parsing failed",
                where="plan_loader",
                repro="Open AGENTS.md and ensure YAML block is valid.",
                fix="Restore valid doctor_plan YAML block per AGENTS.md instructions.",
                risk="Doctor cannot execute full plan.",
                rollback="Use fallback plan until YAML is fixed.",
                verify="Re-run doctor after fixing AGENTS.md.",
                evidence_paths=[plan_error],
            )
        )
        _write_placeholder_set(ctx, plan_error)
        _finalize_reports(ctx)
        _copy_latest(ctx)
        return 1

    steps = doctor_plan.get("steps", [])
    for step in steps:
        action = step["action"]
        step_id = step["id"]
        name = step["name"]
        if action == "overview_discovery":
            result = _run_step(ctx, step_id, name, _overview_discovery)
        elif action == "config_check":
            result = _run_step(ctx, step_id, name, _config_check)
        elif action == "probe_lastfm_minimal":
            result = _run_step(ctx, step_id, name, _probe_lastfm)
        elif action == "probe_musicbrainz_minimal":
            result = _run_step(ctx, step_id, name, _probe_musicbrainz)
        elif action == "soft_probes_optional":
            result = _run_step(ctx, step_id, name, _soft_probes)
        elif action == "build_public":
            result = _run_step(ctx, step_id, name, _build_public)
        elif action == "validate_artifacts":
            result = _run_step(ctx, step_id, name, _validate_artifacts)
        elif action == "render_qa":
            result = _run_step(ctx, step_id, name, _render_qa)
        else:
            result = _run_step(ctx, step_id, name, lambda c, l: (1, []))
            ctx.issues.append(
                Issue(
                    severity="medium",
                    what="Unknown doctor action",
                    where=action,
                    repro="Inspect doctor_plan steps for unsupported action.",
                    fix="Implement the action or correct the plan.",
                    risk="Step skipped.",
                    rollback="Remove unsupported action.",
                    verify="Re-run doctor and confirm action executes.",
                    evidence_paths=[result.log_path],
                )
            )

        if result.exit_code != 0 and step.get("required", False):
            ctx.overall_status = "fail"

    _ensure_fixed_paths(ctx)
    for key, path in ctx.fixed_screenshots.items():
        if not path.exists():
            _write_placeholder_set(ctx, f"Missing screenshot {key}")
            break

    _finalize_reports(ctx)
    _copy_latest(ctx)
    return 0 if ctx.overall_status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(run_doctor())
