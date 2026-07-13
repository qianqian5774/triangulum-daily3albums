from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from daily3albums.artifact_writer import DEFAULT_ARCHIVE_RETENTION_DAYS as WRITER_RETENTION
from daily3albums.config import Env
from scripts.restore_static_archive_seed import (
    DEFAULT_ARCHIVE_RETENTION_DAYS as RESTORE_RETENTION,
)


ROOT = Path(__file__).resolve().parents[1]
RETENTION_DAYS = 7
NODE_ENGINE = ">=22 <25"


def test_archive_retention_authorities_remain_aligned():
    config = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    current_index = json.loads(
        (ROOT / "tests" / "fixtures" / "public_contract" / "current-index.json").read_text(
            encoding="utf-8"
        )
    )
    pages_workflow = (ROOT / ".github" / "workflows" / "pages_daily.yml").read_text(
        encoding="utf-8"
    )
    archive_source = (ROOT / "ui" / "src" / "lib" / "archive.ts").read_text(
        encoding="utf-8"
    )

    assert config["history"]["archive_retention_days"] == RETENTION_DAYS
    assert WRITER_RETENTION == RETENTION_DAYS
    assert RESTORE_RETENTION == RETENTION_DAYS
    assert f"--max-days {RETENTION_DAYS}" in pages_workflow
    assert current_index["archive_retention_days"] == RETENTION_DAYS
    assert f"DEFAULT_ARCHIVE_RETENTION_DAYS = {RETENTION_DAYS}" in archive_source


def test_environment_model_and_examples_only_declare_consumed_provider_inputs():
    assert set(Env.__dataclass_fields__) == {
        "lastfm_api_key",
        "mb_user_agent",
        "discogs_token",
    }

    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    example_names = {
        line.split("=", 1)[0]
        for line in example.splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    assert example_names == {
        "LASTFM_API_KEY",
        "MB_USER_AGENT",
        "DISCOGS_TOKEN",
        "DAILY3ALBUMS_PAGES_BASE_URL",
    }

    pages_workflow = (ROOT / ".github" / "workflows" / "pages_daily.yml").read_text(
        encoding="utf-8"
    )
    for active_name in (
        "DAILY3ALBUMS_PAGES_BASE_URL",
        "LASTFM_API_KEY",
        "MB_USER_AGENT",
        "DISCOGS_TOKEN",
    ):
        assert re.search(rf"^\s+{active_name}:", pages_workflow, re.MULTILINE)

    for inactive_name in (
        "LASTFM_SHARED_SECRET",
        "LISTENBRAINZ_USER_TOKEN",
        "LISTENBRAINZ_USERNAME",
        "DISCOGS_CONSUMER_KEY",
        "DISCOGS_CONSUMER_SECRET",
        "DISCOGS_USER_AGENT",
        "DISCOGS_REQUEST_TOKEN_URL",
        "DISCOGS_AUTHORIZE_URL",
        "DISCOGS_ACCESS_TOKEN_URL",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_ENCRYPTION",
        "SMTP_USERNAME",
        "SMTP_APP_PASSWORD",
    ):
        assert inactive_name not in pages_workflow


def test_node_runtime_range_covers_local_and_tracked_ci_majors():
    package = json.loads((ROOT / "ui" / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((ROOT / "ui" / "package-lock.json").read_text(encoding="utf-8"))
    assert package["engines"]["node"] == NODE_ENGINE
    assert package_lock["packages"][""]["engines"]["node"] == NODE_ENGINE

    for workflow_name in ("ci.yml", "pages_daily.yml"):
        workflow = (ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
        majors = [int(value) for value in re.findall(r'node-version:\s*"(\d+)"', workflow)]
        assert majors
        assert all(22 <= major < 25 for major in majors)
