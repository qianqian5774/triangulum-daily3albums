from daily3albums.constraints import HistoryIndex, validate_today_constraints


def make_pick(album_key: str, artist_keys: list[str], style_key: str, year: int | None = 1995):
    return {
        "album_key": album_key,
        "artist_keys": artist_keys,
        "style_key": style_key,
        "first_release_year": year,
    }


def make_issue(date_key: str, picks: list[dict], decade_theme: str = "1990s"):
    slots = []
    for slot_id in range(3):
        slots.append({"slot_id": slot_id, "theme": "techno", "theme_key": "techno", "picks": picks[slot_id * 3 : slot_id * 3 + 3]})
    return {"date": date_key, "theme_of_day": decade_theme, "constraints": {"min_in_decade": 6, "max_unknown_year": 2}, "slots": slots}


def test_validator_passes_for_unique_day_and_cooldowns():
    picks = [make_pick(f"rg-{i}", [f"artist-{i}"], "techno", year=1990 + i) for i in range(9)]
    issue = make_issue("2026-01-20", picks)
    history = HistoryIndex(album_keys=set(), artist_last_seen={}, style_last_seen={})
    assert validate_today_constraints(issue, history) == []


def test_validator_allows_same_style_key_within_day():
    picks = [make_pick(f"rg-{i}", [f"artist-{i}"], "ambient", year=1991 + i) for i in range(9)]
    issue = make_issue("2026-01-20", picks)
    history = HistoryIndex(album_keys=set(), artist_last_seen={}, style_last_seen={})
    errors = "\n".join(validate_today_constraints(issue, history))
    assert "duplicate style_key" not in errors


def test_validator_catches_duplication_cooldown_and_decade_rules():
    picks = [make_pick(f"rg-{i}", [f"artist-{i}"], "techno", year=1980 + i) for i in range(9)]
    picks[4]["album_key"] = "rg-1"
    picks[5]["artist_keys"] = ["artist-2"]
    picks[0]["first_release_year"] = None
    picks[1]["first_release_year"] = None
    picks[2]["first_release_year"] = None

    issue = make_issue("2026-01-20", picks, decade_theme="1990s")
    history = HistoryIndex(
        album_keys=set(),
        artist_last_seen={"artist-3": "2026-01-14"},
        style_last_seen={"techno": "2026-01-18"},
    )
    errors = "\n".join(validate_today_constraints(issue, history))
    assert "duplicate album_key" in errors
    assert "duplicate artist" in errors
    assert "artist cooldown violation" in errors
    assert "theme cooldown violation" in errors
    assert "decade coverage violation" in errors
    assert "unknown year violation" in errors
