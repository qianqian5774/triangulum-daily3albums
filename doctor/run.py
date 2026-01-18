from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import sys
import textwrap
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from daily3albums.adapters import lastfm_tag_top_albums, musicbrainz_search_release_group
from daily3albums.config import load_config, load_env
from daily3albums.request_broker import RequestBroker


REQUIRED_SCREENSHOTS = {
    "today": "doctor/screenshots/today.svg",
    "archive": "doctor/screenshots/archive.svg",
    "detail": "doctor/screenshots/detail.svg",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(data, encoding="utf-8")


def _write_report_md(path: Path, report: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Daily3Albums Doctor Report")
    lines.append("")
    lines.append(f"- Started: {report.get('started_at')}")
    lines.append(f"- Ended: {report.get('ended_at')}")
    lines.append(f"- Overall Status: {report.get('overall_status')}")
    lines.append("")

    sections = report.get("sections", {})
    for name, info in sections.items():
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- Status: {info.get('status')}")
        detail = info.get("detail")
        if detail:
            lines.append("")
            if isinstance(detail, str):
                lines.append(detail)
            else:
                lines.append("```json")
                lines.append(json.dumps(detail, ensure_ascii=False, indent=2))
                lines.append("```")
        lines.append("")

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _section_error_message(exc: Exception) -> dict[str, Any]:
    return {"error": str(exc), "type": exc.__class__.__name__}


def _run_command(cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "cmd": " ".join(cmd),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _probe_lastfm(repo_root: Path) -> dict[str, Any]:
    env = load_env(repo_root)
    cfg = load_config(repo_root)
    if not env.lastfm_api_key:
        raise RuntimeError("LASTFM_API_KEY missing")
    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies)
    try:
        albums = lastfm_tag_top_albums(
            broker,
            api_key=env.lastfm_api_key,
            tag="electronic",
            limit=1,
        )
        return {"count": len(albums), "sample": [a.__dict__ for a in albums[:1]]}
    finally:
        broker.close()


def _probe_musicbrainz(repo_root: Path) -> dict[str, Any]:
    env = load_env(repo_root)
    cfg = load_config(repo_root)
    if not env.mb_user_agent:
        raise RuntimeError("MB_USER_AGENT missing")
    broker = RequestBroker(repo_root=repo_root, endpoint_policies=cfg.policies)
    try:
        rgs = musicbrainz_search_release_group(
            broker,
            mb_user_agent=env.mb_user_agent,
            title="Discovery",
            artist="Daft Punk",
            limit=1,
        )
        return {"count": len(rgs), "sample": [rg.__dict__ for rg in rgs[:1]]}
    finally:
        broker.close()


def _build_site(repo_root: Path) -> dict[str, Any]:
    build_info = _run_command(["daily3albums", "build", "--tag", "electronic", "--verbose"], cwd=repo_root)
    public_dir = repo_root / "_build" / "public"
    build_info["public_dir"] = str(public_dir)
    build_info["public_exists"] = public_dir.exists()
    if (repo_root / "ui").exists():
        ui_build = _run_command(["npm", "--prefix", "ui", "run", "build"], cwd=repo_root)
        build_info["ui_build"] = ui_build
    return build_info


def _validate_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"path": str(path), "status": "ERROR", "error": str(exc)}
    return {"path": str(path), "status": "OK", "keys": list(data)[:8] if isinstance(data, dict) else None}


def _validate_artifacts(repo_root: Path) -> dict[str, Any]:
    public_dir = repo_root / "_build" / "public"
    data_dir = public_dir / "data"
    archive_dir = data_dir / "archive"
    results: dict[str, Any] = {
        "public_dir": str(public_dir),
        "public_exists": public_dir.exists(),
        "today": None,
        "index": None,
        "archive": [],
        "archive_count": 0,
        "archive_checked": 0,
    }
    if not public_dir.exists():
        return results
    today_path = data_dir / "today.json"
    index_path = data_dir / "index.json"
    results["today"] = _validate_json_file(today_path) if today_path.exists() else {"path": str(today_path), "status": "MISSING"}
    results["index"] = _validate_json_file(index_path) if index_path.exists() else {"path": str(index_path), "status": "MISSING"}

    if archive_dir.exists():
        archive_files = sorted(archive_dir.glob("*.json"))
        results["archive_count"] = len(archive_files)
        for f in archive_files:
            results["archive"].append(_validate_json_file(f))
        results["archive_checked"] = len(archive_files)
    return results


def _extract_first_archive_date(index_payload: Any) -> str | None:
    if not isinstance(index_payload, dict):
        return None
    items = index_payload.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("date"):
                return str(item.get("date"))
    return None


def _fetch_remote(url: str) -> dict[str, Any]:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "daily3albums-doctor"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read()
        return {
            "status": resp.status,
            "content": content,
        }


def _deployment_check(repo_root: Path) -> dict[str, Any]:
    base_url = os.environ.get("DEPLOY_BASE_URL")
    result: dict[str, Any] = {
        "base_url": base_url,
        "comparisons": [],
    }
    if not base_url:
        result["note"] = "DEPLOY_BASE_URL not set; skipping remote comparison"
        return result

    base_url = base_url.rstrip("/")
    public_dir = repo_root / "_build" / "public"
    data_dir = public_dir / "data"
    if not public_dir.exists():
        result["note"] = "Local _build/public missing; cannot compare"
        return result

    local_index = data_dir / "index.json"
    local_today = data_dir / "today.json"
    local_html = public_dir / "index.html"

    local_today_payload = None
    if local_today.exists():
        try:
            local_today_payload = json.loads(local_today.read_text(encoding="utf-8"))
        except Exception:
            local_today_payload = None

    local_date = None
    if isinstance(local_today_payload, dict):
        local_date = local_today_payload.get("date")

    comparisons: list[dict[str, Any]] = []

    def compare_file(local_path: Path, remote_suffix: str) -> None:
        entry: dict[str, Any] = {"local": str(local_path), "remote": f"{base_url}/{remote_suffix}"}
        if not local_path.exists():
            entry["status"] = "MISSING_LOCAL"
            comparisons.append(entry)
            return
        try:
            remote = _fetch_remote(entry["remote"])
            entry["remote_status"] = remote["status"]
            entry["matches"] = remote["content"] == local_path.read_bytes()
        except Exception as exc:
            entry["status"] = "ERROR"
            entry["error"] = str(exc)
        comparisons.append(entry)

    compare_file(local_html, "index.html")
    compare_file(local_today, "data/today.json")
    compare_file(local_index, "data/index.json")

    archive_date = None
    if local_index.exists():
        try:
            index_payload = json.loads(local_index.read_text(encoding="utf-8"))
            archive_date = _extract_first_archive_date(index_payload)
        except Exception:
            archive_date = None

    if archive_date:
        compare_file(data_dir / "archive" / f"{archive_date}.json", f"data/archive/{archive_date}.json")

    result["comparisons"] = comparisons
    result["local_date"] = local_date

    if local_date and base_url:
        try:
            remote_today = _fetch_remote(f"{base_url}/data/today.json")
            remote_payload = json.loads(remote_today["content"].decode("utf-8"))
            result["remote_date"] = remote_payload.get("date")
        except Exception as exc:
            result["remote_date_error"] = str(exc)
    return result


def _pick_free_port() -> int:
    sock = socket.socket()
    sock.bind(("", 0))
    _, port = sock.getsockname()
    sock.close()
    return port


class _SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def _start_static_server(root: Path) -> tuple[ThreadingHTTPServer, str]:
    port = _pick_free_port()

    handler = _SilentHandler
    handler.directory = str(root)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def _playwright_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("playwright.sync_api") is not None


def _write_svg_with_png(path: Path, png_bytes: bytes, title: str) -> None:
    b64 = base64.b64encode(png_bytes).decode("ascii")
    svg = textwrap.dedent(
        f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">
          <title>{title}</title>
          <image href="data:image/png;base64,{b64}" width="1280" height="720" />
        </svg>
        """
    ).strip()
    path.write_text(svg + "\n", encoding="utf-8")


def _write_diagnostic_svg(path: Path, title: str, message: str) -> None:
    svg = textwrap.dedent(
        f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="960" height="540">
          <rect width="100%" height="100%" fill="#111827" />
          <text x="50%" y="45%" fill="#f9fafb" font-size="20" text-anchor="middle" font-family="sans-serif">{title}</text>
          <text x="50%" y="55%" fill="#9ca3af" font-size="14" text-anchor="middle" font-family="sans-serif">{message}</text>
        </svg>
        """
    ).strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg + "\n", encoding="utf-8")


def _navigate_with_fallback(page: Any, urls: list[str]) -> tuple[str | None, list[dict[str, str]]]:
    attempts: list[dict[str, str]] = []
    for url in urls:
        try:
            response = page.goto(url, wait_until="networkidle", timeout=10000)
            ok = response is not None and response.ok
            attempts.append({"url": url, "status": "OK" if ok else "BAD_RESPONSE"})
            if ok:
                return url, attempts
        except Exception as exc:
            attempts.append({"url": url, "status": "ERROR", "error": str(exc)})
    return None, attempts


def _capture_screenshots(repo_root: Path) -> dict[str, Any]:
    public_dir = repo_root / "_build" / "public"
    screenshots_dir = repo_root / "doctor" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {"available": _playwright_available(), "captures": {}}

    if not public_dir.exists():
        report["error"] = "_build/public missing"
        for key, rel in REQUIRED_SCREENSHOTS.items():
            _write_diagnostic_svg(repo_root / rel, key, "_build/public missing")
        return report

    if not _playwright_available():
        report["error"] = "playwright not available"
        for key, rel in REQUIRED_SCREENSHOTS.items():
            _write_diagnostic_svg(repo_root / rel, key, "playwright not available")
        return report

    from playwright.sync_api import sync_playwright

    server, base_url = _start_static_server(public_dir)
    report["base_url"] = base_url

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 720})

            pages = {
                "today": [f"{base_url}/#/", f"{base_url}/"],
                "archive": [f"{base_url}/#/archive", f"{base_url}/archive"],
                "detail": [f"{base_url}/#/", f"{base_url}/"],
            }

            for key, urls in pages.items():
                target, attempts = _navigate_with_fallback(page, urls)
                capture: dict[str, Any] = {"attempts": attempts, "target": target}
                if target:
                    png_bytes = page.screenshot(type="png", full_page=True)
                    _write_svg_with_png(repo_root / REQUIRED_SCREENSHOTS[key], png_bytes, f"{key} screenshot")
                    capture["status"] = "OK"
                else:
                    _write_diagnostic_svg(repo_root / REQUIRED_SCREENSHOTS[key], key, "all routes failed")
                    capture["status"] = "ERROR"
                report["captures"][key] = capture

            browser.close()
    finally:
        server.shutdown()

    return report


def _run_code_health(repo_root: Path) -> dict[str, Any]:
    results: dict[str, Any] = {}

    results["compileall"] = _run_command([sys.executable, "-m", "compileall", "."], cwd=repo_root)
    results["ruff_check"] = _run_command([sys.executable, "-m", "ruff", "check", "."], cwd=repo_root)
    results["ruff_format"] = _run_command([sys.executable, "-m", "ruff", "format", "--check", "."], cwd=repo_root)
    pytest = _run_command([sys.executable, "-m", "pytest"], cwd=repo_root)
    results["pytest"] = pytest

    if "no tests ran" in pytest.get("stdout", "") + pytest.get("stderr", ""):
        results["pytest"]["note"] = "no tests ran"
    return results


def _ensure_test_smoke(repo_root: Path) -> dict[str, Any] | None:
    tests_dir = repo_root / "tests"
    smoke_path = tests_dir / "test_smoke.py"
    if smoke_path.exists():
        return None
    tests_dir.mkdir(parents=True, exist_ok=True)
    smoke_path.write_text(
        """
        def test_imports():
            import daily3albums

            assert daily3albums.__name__ == "daily3albums"
        """.strip()
        + "\n",
        encoding="utf-8",
    )
    return {"created": str(smoke_path)}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report_path = repo_root / "doctor" / "REPORT.json"
    report_md = repo_root / "REPORT.md"

    report: dict[str, Any] = {
        "status": "RUNNING",
        "overall_status": "RUNNING",
        "started_at": _utc_now(),
        "ended_at": None,
        "sections": {},
    }
    _write_json(report_path, report)

    overall_fail_reasons: list[str] = []
    warn_sections: list[str] = []

    def set_section(name: str, status: str, detail: Any) -> None:
        report["sections"][name] = {"status": status, "detail": detail}
        _write_json(report_path, report)

    try:
        try:
            lastfm_detail = _probe_lastfm(repo_root)
            set_section("lastfm_probe", "PASS", lastfm_detail)
        except Exception as exc:
            set_section("lastfm_probe", "ERROR", _section_error_message(exc))
            overall_fail_reasons.append("lastfm_probe")

        try:
            mb_detail = _probe_musicbrainz(repo_root)
            set_section("musicbrainz_probe", "PASS", mb_detail)
        except Exception as exc:
            set_section("musicbrainz_probe", "ERROR", _section_error_message(exc))
            overall_fail_reasons.append("musicbrainz_probe")

        try:
            build_detail = _build_site(repo_root)
            build_status = "PASS" if build_detail.get("returncode") == 0 else "WARN"
            if not build_detail.get("public_exists"):
                build_status = "ERROR"
                overall_fail_reasons.append("build_public_missing")
            set_section("build", build_status, build_detail)
            if build_status != "PASS":
                warn_sections.append("build")
        except Exception as exc:
            set_section("build", "ERROR", _section_error_message(exc))
            overall_fail_reasons.append("build_public_missing")

        try:
            validation_detail = _validate_artifacts(repo_root)
            status = "PASS"
            if not validation_detail.get("public_exists"):
                status = "WARN"
            else:
                errors = [
                    entry
                    for entry in [validation_detail.get("today"), validation_detail.get("index")]
                    if isinstance(entry, dict) and entry.get("status") not in ("OK", None)
                ]
                archive_errors = [
                    entry for entry in validation_detail.get("archive", []) if entry.get("status") != "OK"
                ]
                if errors or archive_errors:
                    status = "WARN"
            set_section("artifact_validation", status, validation_detail)
            if status != "PASS":
                warn_sections.append("artifact_validation")
        except Exception as exc:
            set_section("artifact_validation", "ERROR", _section_error_message(exc))
            warn_sections.append("artifact_validation")

        try:
            deploy_detail = _deployment_check(repo_root)
            status = "PASS"
            base_url = deploy_detail.get("base_url")
            if not base_url:
                status = "WARN"
            else:
                mismatches = [c for c in deploy_detail.get("comparisons", []) if c.get("matches") is False]
                if mismatches:
                    status = "WARN"
                local_date = deploy_detail.get("local_date")
                remote_date = deploy_detail.get("remote_date")
                if local_date and remote_date and local_date != remote_date:
                    status = "FAIL"
                    overall_fail_reasons.append("deploy_date_mismatch")
            set_section("deployment_check", status, deploy_detail)
            if status != "PASS":
                warn_sections.append("deployment_check")
        except Exception as exc:
            set_section("deployment_check", "ERROR", _section_error_message(exc))
            warn_sections.append("deployment_check")

        try:
            code_health = _run_code_health(repo_root)
            status = "PASS"
            for key, info in code_health.items():
                if info.get("returncode") != 0:
                    status = "WARN"
            if "no tests ran" in str(code_health.get("pytest", {})):
                status = "WARN"
                smoke = _ensure_test_smoke(repo_root)
                if smoke:
                    code_health["pytest_smoke"] = smoke
            set_section("code_health", status, code_health)
            if status != "PASS":
                warn_sections.append("code_health")
        except Exception as exc:
            set_section("code_health", "ERROR", _section_error_message(exc))
            warn_sections.append("code_health")

        try:
            screenshots = _capture_screenshots(repo_root)
            status = "PASS" if not screenshots.get("error") else "WARN"
            set_section("screenshots", status, screenshots)
            if status != "PASS":
                warn_sections.append("screenshots")
        except Exception as exc:
            set_section("screenshots", "ERROR", _section_error_message(exc))
            warn_sections.append("screenshots")

    finally:
        report["ended_at"] = _utc_now()
        if overall_fail_reasons:
            report["overall_status"] = "FAIL"
        elif warn_sections:
            report["overall_status"] = "WARN"
        else:
            report["overall_status"] = "PASS"
        report["status"] = "COMPLETE"
        _write_json(report_path, report)
        _write_report_md(report_md, report)

        for key, rel_path in REQUIRED_SCREENSHOTS.items():
            path = repo_root / rel_path
            if not path.exists():
                _write_diagnostic_svg(path, key, "missing screenshot artifact")

    required_paths = [report_md, report_path] + [repo_root / path for path in REQUIRED_SCREENSHOTS.values()]
    missing = [str(p) for p in required_paths if not p.exists()]
    if missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
