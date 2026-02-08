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
    lastfm_page_start: int
    lastfm_max_pages: int
    max_tag_tries_per_slot: int
    mb_max_queries_per_candidate: int
    mb_max_candidates_per_slot: int
    mb_time_budget_s_per_slot: float
    coarse_top_n_per_slot: int
    discogs_enabled: bool
    discogs_page_start: int
    discogs_max_pages: int
    discogs_per_page: int
    decade_mode: str
    ignored_legacy_decade_keys: list[str]
    ui_build_timeout_s: int


def load_config(repo_root: Path) -> AppConfig:
    cfg = load_yaml(repo_root / "config" / "config.yaml")
    policies = load_yaml(repo_root / "config" / "endpoint_policies.yaml")
    tz_override = os.environ.get("DAILY3ALBUMS_TZ")
    tz = (tz_override or cfg.get("timezone") or "Asia/Shanghai").strip()
    candidate_lastfm_cfg = (cfg.get("candidates", {}) or {}).get("lastfm", {})
    build_cfg = cfg.get("build", {}) or {}
    lastfm_page_start = int(candidate_lastfm_cfg.get("lastfm_page_start", candidate_lastfm_cfg.get("page_start", 1)))
    lastfm_max_pages = int(candidate_lastfm_cfg.get("lastfm_max_pages", build_cfg.get("lastfm_max_pages", 6)))
    max_tag_tries_per_slot = int(build_cfg.get("max_tag_tries_per_slot", 8))
    normalizer_cfg = cfg.get("normalizer", {}) or {}
    scoring_cfg = cfg.get("scoring", {}) or {}
    mb_max_queries_per_candidate = int(normalizer_cfg.get("mb_max_queries_per_candidate", 3))
    mb_max_candidates_per_slot = int(normalizer_cfg.get("mb_max_candidates_per_slot", 120))
    mb_time_budget_s_per_slot = float(normalizer_cfg.get("mb_time_budget_s_per_slot", 90.0))
    coarse_top_n_per_slot = int(scoring_cfg.get("coarse_top_n_per_slot", scoring_cfg.get("mb_prefilter_topn", 120)))
    discogs_cfg = (cfg.get("candidates", {}) or {}).get("discogs", {}) or {}
    discogs_enabled = bool(discogs_cfg.get("enabled", True))
    discogs_page_start = max(1, int(discogs_cfg.get("discogs_page_start", discogs_cfg.get("page_start", 1))))
    discogs_max_pages = max(1, int(discogs_cfg.get("discogs_max_pages", discogs_cfg.get("max_pages", 3))))
    discogs_per_page = min(100, max(1, int(discogs_cfg.get("discogs_per_page", discogs_cfg.get("per_page", 100)))))
    raw_decade_mode = str(cfg.get("decade_mode", "off") or "off").strip().lower()
    decade_mode = "on" if raw_decade_mode == "on" else "off"
    ui_build_timeout_s = int((cfg.get("build", {}) or {}).get("ui_build_timeout_s", 300))
    legacy_decade_keys = [
        key for key in ("decade_theme", "min_in_decade", "max_unknown_year", "decade_axis", "day_decade")
        if key in build_cfg or key in cfg
    ]
    return AppConfig(
        raw=cfg,
        policies=policies,
        timezone=tz,
        lastfm_page_start=lastfm_page_start,
        lastfm_max_pages=lastfm_max_pages,
        max_tag_tries_per_slot=max_tag_tries_per_slot,
        mb_max_queries_per_candidate=mb_max_queries_per_candidate,
        mb_max_candidates_per_slot=mb_max_candidates_per_slot,
        mb_time_budget_s_per_slot=mb_time_budget_s_per_slot,
        coarse_top_n_per_slot=coarse_top_n_per_slot,
        discogs_enabled=discogs_enabled,
        discogs_page_start=discogs_page_start,
        discogs_max_pages=discogs_max_pages,
        discogs_per_page=discogs_per_page,
        decade_mode=decade_mode,
        ignored_legacy_decade_keys=legacy_decade_keys,
        ui_build_timeout_s=max(1, int(ui_build_timeout_s)),
    )
