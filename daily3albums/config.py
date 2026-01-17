from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class Env:
    lastfm_api_key: str | None
    mb_user_agent: str | None

    alert_smtp_host: str | None
    alert_smtp_port: int | None
    alert_smtp_user: str | None
    alert_smtp_pass: str | None
    alert_mail_from: str | None
    alert_mail_to: str | None

    r2_access_key_id: str | None
    r2_secret_access_key: str | None
    r2_endpoint: str | None
    r2_bucket: str | None

    discogs_token: str | None
    listenbrainz_token: str | None
    openai_api_key: str | None


def _g(name: str) -> str | None:
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return None
    return v.strip()


def load_env(repo_root: Path) -> Env:
    # 本地：读 .env；线上（GitHub Actions）：没有 .env 也没关系，直接读 os.environ
    load_dotenv(repo_root / ".env", override=False)

    port = _g("ALERT_SMTP_PORT")
    return Env(
        lastfm_api_key=_g("LASTFM_API_KEY"),
        mb_user_agent=_g("MB_USER_AGENT"),

        alert_smtp_host=_g("ALERT_SMTP_HOST"),
        alert_smtp_port=int(port) if port else None,
        alert_smtp_user=_g("ALERT_SMTP_USER"),
        alert_smtp_pass=_g("ALERT_SMTP_PASS"),
        alert_mail_from=_g("ALERT_MAIL_FROM"),
        alert_mail_to=_g("ALERT_MAIL_TO"),

        r2_access_key_id=_g("R2_ACCESS_KEY_ID"),
        r2_secret_access_key=_g("R2_SECRET_ACCESS_KEY"),
        r2_endpoint=_g("R2_ENDPOINT"),
        r2_bucket=_g("R2_BUCKET"),

        discogs_token=_g("DISCOGS_TOKEN"),
        listenbrainz_token=_g("LISTENBRAINZ_TOKEN"),
        openai_api_key=_g("OPENAI_API_KEY"),
    )


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class AppConfig:
    raw: dict
    policies: dict
    timezone: str


def load_config(repo_root: Path) -> AppConfig:
    cfg = load_yaml(repo_root / "config" / "config.yaml")
    policies = load_yaml(repo_root / "config" / "endpoint_policies.yaml")
    tz_override = os.environ.get("DAILY3ALBUMS_TZ")
    tz = (tz_override or cfg.get("timezone") or "Asia/Taipei").strip()
    return AppConfig(raw=cfg, policies=policies, timezone=tz)
