from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import yaml

from daily3albums import cli
from daily3albums.config import AppConfig, load_config


def _write_config(repo_root: Path, payload: dict) -> None:
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "endpoint_policies.yaml").write_text("{}\n", encoding="utf-8")
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _active_projection(config: AppConfig) -> dict:
    return {
        field.name: getattr(config, field.name)
        for field in fields(AppConfig)
        if field.name not in {"raw", "policies"}
    }


def test_repository_config_exposes_only_truthful_active_or_reserved_surfaces():
    repo_root = Path(__file__).resolve().parents[1]
    config = load_config(repo_root)
    raw = config.raw

    for removed_top_level in (
        "schema_version",
        "output_schema_version",
        "timezone",
        "random_seed_strategy",
        "decade_mode",
        "global_exclusions",
        "slots",
        "themes",
    ):
        assert removed_top_level not in raw

    assert raw["normalizer"] == {
        "policy_version": "td02b-v1",
        "min_confidence": 0.82,
        "hard_confidence_floor": 0.78,
        "ambiguity_gap": 0.08,
        "identity_title_floor": 0.60,
        "identity_artist_floor": 0.50,
        "hard_ambiguity_policy": "reject_distinct",
        "mb_max_queries_per_candidate": 3,
        "mb_max_candidates_per_slot": 100,
        "mb_time_budget_s_per_slot": 60,
    }
    assert raw["candidates"]["lastfm"] == {
        "lastfm_page_start": 1,
        "lastfm_max_pages": 6,
    }
    assert raw["candidates"]["discogs"] == {
        "enabled": True,
        "discogs_page_start": 1,
        "discogs_max_pages": 3,
        "discogs_per_page": 100,
    }
    assert "listenbrainz" not in raw["candidates"]
    assert raw["scoring"] == {"coarse_top_n_per_slot": 100}
    assert raw["build"] == {"max_tag_tries_per_slot": 8, "ui_build_timeout_s": 300}


def test_active_config_values_are_loaded_into_their_runtime_projection():
    repo_root = Path(__file__).resolve().parents[1]
    config = load_config(repo_root)

    assert config.archive_retention_days == 7
    assert config.dedupe_same_rg_days == 7
    assert config.dedupe_same_artist_days == 7
    assert config.mb_max_queries_per_candidate == 3
    assert config.mb_max_candidates_per_slot == 100
    assert config.mb_time_budget_s_per_slot == 60.0
    assert config.normalization_policy.policy_version == "td02b-v1"
    assert config.normalization_policy.min_confidence == 0.82
    assert config.normalization_policy.hard_confidence_floor == 0.78
    assert config.lastfm_page_start == 1
    assert config.lastfm_max_pages == 6
    assert config.discogs_enabled is True
    assert config.discogs_page_start == 1
    assert config.discogs_max_pages == 3
    assert config.discogs_per_page == 100
    assert config.coarse_top_n_per_slot == 100
    assert config.max_tag_tries_per_slot == 8
    assert config.ui_build_timeout_s == 300


def test_tag_pool_and_allow_types_have_real_build_consumers():
    config = load_config(Path(__file__).resolve().parents[1])

    assert cli._get_tag_pool(config) == config.raw["tag_pool"]
    flags = cli._type_flags_from_cfg(config)
    assert flags == {
        "album": True,
        "compilation": False,
        "live": False,
        "ep": True,
        "single": False,
    }
    assert cli._primary_type_allowed("Album", flags) is True
    assert cli._primary_type_allowed("EP", flags) is True
    assert cli._primary_type_allowed("Single", flags) is False


def test_canonical_candidate_keys_take_precedence_over_deprecated_aliases(tmp_path: Path):
    _write_config(
        tmp_path,
        {
            "candidates": {
                "lastfm": {
                    "lastfm_page_start": 2,
                    "page_start": 9,
                    "lastfm_max_pages": 5,
                },
                "discogs": {
                    "discogs_page_start": 3,
                    "page_start": 8,
                    "discogs_max_pages": 4,
                    "max_pages": 9,
                    "discogs_per_page": 80,
                    "per_page": 10,
                },
            },
            "scoring": {"coarse_top_n_per_slot": 70, "mb_prefilter_topn": 20},
            "build": {"lastfm_max_pages": 12},
        },
    )

    config = load_config(tmp_path)

    assert config.lastfm_page_start == 2
    assert config.lastfm_max_pages == 5
    assert config.discogs_page_start == 3
    assert config.discogs_max_pages == 4
    assert config.discogs_per_page == 80
    assert config.coarse_top_n_per_slot == 70


def test_deprecated_candidate_aliases_remain_compatible_when_canonical_keys_are_absent(tmp_path: Path):
    _write_config(
        tmp_path,
        {
            "candidates": {
                "lastfm": {"page_start": 4},
                "discogs": {"page_start": 5, "max_pages": 6, "per_page": 40},
            },
            "scoring": {"mb_prefilter_topn": 55},
            "build": {"lastfm_max_pages": 7},
        },
    )

    config = load_config(tmp_path)

    assert config.lastfm_page_start == 4
    assert config.lastfm_max_pages == 7
    assert config.discogs_page_start == 5
    assert config.discogs_max_pages == 6
    assert config.discogs_per_page == 40
    assert config.coarse_top_n_per_slot == 55


def test_removed_fields_do_not_change_the_active_runtime_projection(tmp_path: Path):
    baseline_root = tmp_path / "baseline"
    removed_root = tmp_path / "with-removed-fields"
    baseline = {
        "history": {
            "archive_retention_days": 7,
            "dedupe_same_rg_days": 7,
            "dedupe_same_artist_days": 7,
        },
        "normalizer": {
            "policy_version": "td02b-v1",
            "min_confidence": 0.82,
            "hard_confidence_floor": 0.78,
            "ambiguity_gap": 0.08,
            "identity_title_floor": 0.60,
            "identity_artist_floor": 0.50,
            "hard_ambiguity_policy": "reject_distinct",
            "mb_max_queries_per_candidate": 3,
            "mb_max_candidates_per_slot": 100,
            "mb_time_budget_s_per_slot": 60,
        },
        "candidates": {
            "lastfm": {"lastfm_page_start": 1, "lastfm_max_pages": 6},
            "discogs": {
                "enabled": True,
                "discogs_page_start": 1,
                "discogs_max_pages": 3,
                "discogs_per_page": 100,
            },
        },
        "scoring": {"coarse_top_n_per_slot": 100},
        "build": {"max_tag_tries_per_slot": 8, "ui_build_timeout_s": 300},
    }
    with_removed = yaml.safe_load(yaml.safe_dump(baseline))
    with_removed.update(
        {
            "schema_version": "99",
            "output_schema_version": "99",
            "timezone": "UTC",
            "random_seed_strategy": "random",
            "global_exclusions": {"allow_primary_types": ["Single"]},
            "slots": {"Headliner": {"require_cover": False, "weights": {"Q": 999}}},
            "themes": {"rotation": "hourly", "items": [{"seed_tags": ["changed"]}]},
        }
    )
    with_removed["normalizer"].update(
        {"top_k": 999, "weights": {"title": 999}, "unused_future_field": "ignored"}
    )
    with_removed["candidates"]["lastfm"].update(
        {"per_page": 999, "pages_per_call": 999, "deepcut_min_page": 999}
    )
    with_removed["candidates"]["discogs"]["deepcut_min_page"] = 999
    with_removed["candidates"]["listenbrainz"] = {"count": 999, "deepcut_min_offset": 999}
    with_removed["scoring"].update(
        {
            "multi_source_bonus": 999,
            "temperature_by_slot": {"0": 999},
            "mb_normalize_budget_cap": 999,
            "coarse_top_n": 999,
        }
    )

    _write_config(baseline_root, baseline)
    _write_config(removed_root, with_removed)

    assert _active_projection(load_config(baseline_root)) == _active_projection(load_config(removed_root))
