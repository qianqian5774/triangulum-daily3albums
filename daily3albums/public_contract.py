from __future__ import annotations

import re
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Mapping


ArtifactKind = Literal["today", "archive", "index"]
ContractProfile = Literal["current", "legacy"]

CURRENT_OUTPUT_SCHEMA_VERSION = "1.0"
LEGACY_ARCHIVE_SCHEMA_VERSIONS = frozenset({"1"})
SLOT_IDS = (0, 1, 2)
PICK_ROLES = ("Headliner", "Lineage", "DeepCut")

_MBID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@dataclass(frozen=True)
class ContractViolation:
    code: str
    message: str


class PublicContractError(ValueError):
    def __init__(self, code: str, message: str):
        self.violation = ContractViolation(code=code, message=message)
        super().__init__(f"{code}: {message}")

    @property
    def code(self) -> str:
        return self.violation.code


def _fail(code: str, message: str) -> None:
    raise PublicContractError(code, message)


def _record(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("WRONG_TYPE", f"{field} must be an object")
    return value


def _required_str(obj: Mapping[str, Any], field: str, path: str = "") -> str:
    label = f"{path}.{field}" if path else field
    if field not in obj:
        _fail("MISSING_REQUIRED_FIELD", f"{label} is required")
    value = obj[field]
    if value is None:
        _fail("NULL_REQUIRED_FIELD", f"{label} cannot be null")
    if not isinstance(value, str):
        _fail("WRONG_TYPE", f"{label} must be a string")
    if not value.strip():
        _fail("EMPTY_REQUIRED_FIELD", f"{label} cannot be empty")
    return value


def _optional_str_or_null(obj: Mapping[str, Any], field: str, path: str) -> None:
    if field not in obj or obj[field] is None:
        return
    if not isinstance(obj[field], str):
        _fail("WRONG_TYPE", f"{path}.{field} must be a string or null")


def _optional_number_or_null(obj: Mapping[str, Any], field: str, path: str) -> None:
    if field not in obj or obj[field] is None:
        return
    value = obj[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        _fail("WRONG_TYPE", f"{path}.{field} must be a number or null")


def _validate_date(value: str, field: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        _fail("INVALID_DATE", f"{field} must be YYYY-MM-DD")


def _validate_schema_version(payload: Mapping[str, Any], *, profile: ContractProfile) -> str:
    version = _required_str(payload, "output_schema_version")
    if profile == "current":
        if version != CURRENT_OUTPUT_SCHEMA_VERSION:
            _fail("UNKNOWN_SCHEMA_VERSION", f"current output_schema_version={version!r} is unsupported")
    elif version not in LEGACY_ARCHIVE_SCHEMA_VERSIONS:
        _fail("UNKNOWN_SCHEMA_VERSION", f"legacy archive output_schema_version={version!r} is unsupported")
    return version


def archive_profile_for_payload(payload: Any) -> ContractProfile:
    obj = _record(payload, "archive")
    version = obj.get("output_schema_version")
    if not isinstance(version, str):
        if version is None:
            _fail("MISSING_REQUIRED_FIELD", "output_schema_version is required")
        _fail("WRONG_TYPE", "output_schema_version must be a string")
    if version == CURRENT_OUTPUT_SCHEMA_VERSION:
        return "current"
    if version in LEGACY_ARCHIVE_SCHEMA_VERSIONS:
        return "legacy"
    _fail("UNKNOWN_SCHEMA_VERSION", f"archive output_schema_version={version!r} is unsupported")


def _validate_cover(pick: Mapping[str, Any], path: str, *, current: bool) -> None:
    if "cover" not in pick:
        _fail("MISSING_REQUIRED_FIELD", f"{path}.cover is required")
    cover = _record(pick["cover"], f"{path}.cover")
    if current and "has_cover" not in cover:
        _fail("MISSING_REQUIRED_FIELD", f"{path}.cover.has_cover is required")
    if "has_cover" in cover and not isinstance(cover["has_cover"], bool):
        _fail("WRONG_TYPE", f"{path}.cover.has_cover must be a boolean")
    _required_str(cover, "optimized_cover_url", f"{path}.cover")
    _optional_str_or_null(cover, "cover_version", f"{path}.cover")
    _optional_str_or_null(cover, "original_cover_url", f"{path}.cover")


def _validate_tag_list(value: Any, path: str) -> None:
    if not isinstance(value, list):
        _fail("WRONG_TYPE", f"{path} must be an array")
    for index, item in enumerate(value):
        tag = _record(item, f"{path}[{index}]")
        _required_str(tag, "name", f"{path}[{index}]")
        _optional_str_or_null(tag, "source", f"{path}[{index}]")
        _optional_number_or_null(tag, "count", f"{path}[{index}]")


def _validate_optional_metadata(pick: Mapping[str, Any], path: str) -> None:
    _optional_number_or_null(pick, "first_release_year", path)
    if "tags" in pick and pick["tags"] is not None:
        _validate_tag_list(pick["tags"], f"{path}.tags")
    if "reason" in pick and pick["reason"] is not None and not isinstance(pick["reason"], str):
        _fail("WRONG_TYPE", f"{path}.reason must be a string or null")
    for object_field in ("musicbrainz", "links", "evidence"):
        if object_field in pick and pick[object_field] is not None and not isinstance(pick[object_field], dict):
            _fail("WRONG_TYPE", f"{path}.{object_field} must be an object or null")

    musicbrainz = pick.get("musicbrainz")
    if isinstance(musicbrainz, dict):
        rating = musicbrainz.get("rating")
        if rating is not None:
            rating_obj = _record(rating, f"{path}.musicbrainz.rating")
            if "value" not in rating_obj:
                _fail("MISSING_REQUIRED_FIELD", f"{path}.musicbrainz.rating.value is required")
            value = rating_obj["value"]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                _fail("WRONG_TYPE", f"{path}.musicbrainz.rating.value must be a number")
            _optional_number_or_null(rating_obj, "votes_count", f"{path}.musicbrainz.rating")
        if "tags" in musicbrainz and musicbrainz["tags"] is not None:
            _validate_tag_list(musicbrainz["tags"], f"{path}.musicbrainz.tags")
        _optional_str_or_null(musicbrainz, "wikipedia_url", f"{path}.musicbrainz")
        overview = musicbrainz.get("overview")
        if overview is not None:
            overview_obj = _record(overview, f"{path}.musicbrainz.overview")
            _required_str(overview_obj, "text", f"{path}.musicbrainz.overview")
            for field in ("source", "source_url", "license_url"):
                _optional_str_or_null(overview_obj, field, f"{path}.musicbrainz.overview")

    links = pick.get("links")
    if isinstance(links, dict):
        for field in ("musicbrainz", "lastfm", "youtube_search"):
            _optional_str_or_null(links, field, f"{path}.links")

    evidence = pick.get("evidence")
    if isinstance(evidence, dict):
        _optional_number_or_null(evidence, "mapping_confidence", f"{path}.evidence")


def _validate_current_pick(value: Any, path: str) -> dict[str, Any]:
    pick = _record(value, path)
    role = _required_str(pick, "slot", path)
    if role not in PICK_ROLES:
        _fail("INVALID_SLOT_ENUM", f"{path}.slot={role!r} is unsupported")
    _required_str(pick, "title", path)
    _required_str(pick, "artist_credit", path)
    rg_mbid = _required_str(pick, "rg_mbid", path)
    if not _MBID_RE.fullmatch(rg_mbid):
        _fail("INVALID_RELEASE_GROUP_MBID", f"{path}.rg_mbid is not a MusicBrainz UUID")
    _validate_cover(pick, path, current=True)
    _validate_optional_metadata(pick, path)
    return pick


def _validate_legacy_pick(value: Any, path: str) -> dict[str, Any]:
    pick = _record(value, path)
    role = _required_str(pick, "slot", path)
    if role not in PICK_ROLES:
        _fail("INVALID_SLOT_ENUM", f"{path}.slot={role!r} is unsupported")
    title = _required_str(pick, "title", path)
    artist = _required_str(pick, "artist_credit", path)
    rg_mbid = pick.get("rg_mbid")
    if rg_mbid is not None:
        if not isinstance(rg_mbid, str):
            _fail("WRONG_TYPE", f"{path}.rg_mbid must be a string or null")
        if rg_mbid and not _MBID_RE.fullmatch(rg_mbid):
            _fail("INVALID_RELEASE_GROUP_MBID", f"{path}.rg_mbid is not a MusicBrainz UUID")
    if not rg_mbid:
        album_key = pick.get("album_key")
        if album_key is not None and not isinstance(album_key, str):
            _fail("WRONG_TYPE", f"{path}.album_key must be a string")
        if not (isinstance(album_key, str) and album_key.strip()) and not (title.strip() and artist.strip()):
            _fail("MISSING_STABLE_ALBUM_IDENTITY", f"{path} has no stable legacy album identity")
    _validate_cover(pick, path, current=False)
    _validate_optional_metadata(pick, path)
    return pick


def _validate_current_issue(payload: Any, artifact_kind: Literal["today", "archive"]) -> dict[str, Any]:
    issue = _record(payload, artifact_kind)
    _validate_schema_version(issue, profile="current")
    date = _required_str(issue, "date")
    _validate_date(date, "date")
    _required_str(issue, "run_id")
    _required_str(issue, "theme_of_day")

    if "now_slot_id" not in issue:
        _fail("MISSING_REQUIRED_FIELD", "now_slot_id is required")
    now_slot_id = issue["now_slot_id"]
    if isinstance(now_slot_id, bool) or not isinstance(now_slot_id, int):
        _fail("WRONG_TYPE", "now_slot_id must be an integer")
    if now_slot_id not in SLOT_IDS:
        _fail("INVALID_SLOT_ID", f"now_slot_id={now_slot_id!r} is unsupported")

    slots = issue.get("slots")
    if not isinstance(slots, list):
        _fail("WRONG_TYPE", "slots must be an array")
    if len(slots) != 3:
        _fail("INVALID_3X3_STRUCTURE", "slots must contain exactly 3 items")

    parsed_slots: list[dict[str, Any]] = []
    for slot_index, value in enumerate(slots):
        slot = _record(value, f"slots[{slot_index}]")
        if "slot_id" not in slot:
            _fail("MISSING_REQUIRED_FIELD", f"slots[{slot_index}].slot_id is required")
        slot_id = slot["slot_id"]
        if isinstance(slot_id, bool) or not isinstance(slot_id, int):
            _fail("WRONG_TYPE", f"slots[{slot_index}].slot_id must be an integer")
        _required_str(slot, "window_label", f"slots[{slot_index}]")
        _required_str(slot, "theme", f"slots[{slot_index}]")
        picks = slot.get("picks")
        if not isinstance(picks, list):
            _fail("WRONG_TYPE", f"slots[{slot_index}].picks must be an array")
        if len(picks) != 3:
            _fail("INVALID_3X3_STRUCTURE", f"slots[{slot_index}].picks must contain exactly 3 items")
        parsed = [_validate_current_pick(pick, f"slots[{slot_index}].picks[{pick_index}]") for pick_index, pick in enumerate(picks)]
        roles = tuple(pick["slot"] for pick in parsed)
        if roles != PICK_ROLES:
            _fail("INVALID_SLOT_COVERAGE", f"slots[{slot_index}] roles must be {list(PICK_ROLES)!r}")
        parsed_slots.append(slot)

    slot_ids = tuple(slot["slot_id"] for slot in parsed_slots)
    if slot_ids != SLOT_IDS:
        _fail("INVALID_SLOT_COVERAGE", f"slot ids must be ordered {list(SLOT_IDS)!r}")

    top_picks = issue.get("picks")
    if not isinstance(top_picks, list):
        _fail("WRONG_TYPE", "picks must be an array")
    if len(top_picks) != 3:
        _fail("INVALID_3X3_STRUCTURE", "top-level picks must contain exactly 3 items")
    [_validate_current_pick(pick, f"picks[{index}]") for index, pick in enumerate(top_picks)]
    expected_top_picks = parsed_slots[now_slot_id]["picks"]
    if top_picks != expected_top_picks:
        _fail("TOP_LEVEL_PICKS_MISMATCH", "top-level picks must equal slots[now_slot_id].picks")
    return issue


def _validate_legacy_archive(payload: Any) -> dict[str, Any]:
    issue = _record(payload, "archive")
    _validate_schema_version(issue, profile="legacy")
    date = _required_str(issue, "date")
    _validate_date(date, "date")
    _required_str(issue, "run_id")
    _required_str(issue, "theme_of_day")
    picks = issue.get("picks")
    if not isinstance(picks, list):
        _fail("WRONG_TYPE", "legacy archive picks must be an array")
    if not picks:
        _fail("INVALID_3X3_STRUCTURE", "legacy archive picks cannot be empty")
    [_validate_legacy_pick(pick, f"picks[{index}]") for index, pick in enumerate(picks)]
    if "slots" in issue and issue["slots"] is not None:
        if not isinstance(issue["slots"], list):
            _fail("WRONG_TYPE", "legacy archive slots must be an array when present")
    return issue


def validate_issue(
    payload: Any,
    *,
    artifact_kind: Literal["today", "archive"],
    profile: ContractProfile,
) -> dict[str, Any]:
    if artifact_kind == "today" and profile != "current":
        _fail("UNSUPPORTED_PROFILE", "legacy today payloads are not supported")
    if profile == "current":
        return _validate_current_issue(payload, artifact_kind)
    if artifact_kind != "archive":
        _fail("UNSUPPORTED_PROFILE", "legacy profile is only supported for archive payloads")
    return _validate_legacy_archive(payload)


def validate_archive(payload: Any) -> tuple[dict[str, Any], ContractProfile]:
    profile = archive_profile_for_payload(payload)
    return validate_issue(payload, artifact_kind="archive", profile=profile), profile


def validate_index(payload: Any) -> dict[str, Any]:
    index = _record(payload, "index")
    _validate_schema_version(index, profile="current")
    items = index.get("items")
    if not isinstance(items, list):
        _fail("WRONG_TYPE", "index.items must be an array")
    identities: set[tuple[str, str]] = set()
    dates: set[str] = set()
    for item_index, value in enumerate(items):
        item = _record(value, f"items[{item_index}]")
        date = _required_str(item, "date", f"items[{item_index}]")
        _validate_date(date, f"items[{item_index}].date")
        run_id = _required_str(item, "run_id", f"items[{item_index}]")
        identity = (date, run_id)
        if identity in identities or date in dates:
            _fail("DUPLICATE_ARCHIVE_IDENTITY", f"duplicate/conflicting archive identity for date={date}")
        identities.add(identity)
        dates.add(date)
        _optional_str_or_null(item, "theme_of_day", f"items[{item_index}]")
        _optional_str_or_null(item, "run_at", f"items[{item_index}]")
        if "slot" in item and item["slot"] is not None:
            slot = item["slot"]
            if isinstance(slot, bool) or not isinstance(slot, int):
                _fail("WRONG_TYPE", f"items[{item_index}].slot must be an integer or null")
    if "archive_retention_days" in index and index["archive_retention_days"] is not None:
        retention = index["archive_retention_days"]
        if isinstance(retention, bool) or not isinstance(retention, int):
            _fail("WRONG_TYPE", "archive_retention_days must be an integer or null")
        if retention < 1:
            _fail("INVALID_VALUE", "archive_retention_days must be >= 1")
    return index


def canonical_archive_paths(date: str, run_id: str) -> tuple[str, str]:
    return (f"data/archive/{date}/{run_id}.json", f"data/archive/{date}.json")


def validate_archive_identity(payload: Mapping[str, Any], *, date: str, run_id: str) -> None:
    if payload.get("date") != date:
        _fail("ARCHIVE_IDENTITY_MISMATCH", f"archive date does not match index date={date}")
    if payload.get("run_id") != run_id:
        _fail("ARCHIVE_IDENTITY_MISMATCH", f"archive run_id does not match index run_id={run_id}")


def require_byte_identical(first: bytes, second: bytes) -> None:
    if first != second:
        _fail("ARCHIVE_ALIAS_BYTES_MISMATCH", "run-specific archive and date alias must be byte-identical")
