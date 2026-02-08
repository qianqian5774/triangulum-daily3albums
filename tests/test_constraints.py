from daily3albums.constraints import HistoryIndex, validate_today_constraints


def make_pick(album_key: str, artist_keys: list[str], style_key: str):
    return {
        "album_key": album_key,
        "artist_keys": artist_keys,
        "style_key": style_key,
    }


def make_issue(date_key: str, picks: list[dict]):
    slots = []
    for slot_id in range(3):
        slots.append({"slot_id": slot_id, "picks": picks[slot_id * 3 : slot_id * 3 + 3]})
    return {"date": date_key, "slots": slots}


def test_validator_passes_for_unique_day_and_cooldowns():
    picks = [make_pick(f"rg-{i}", [f"artist-{i}"], f"style-{i}") for i in range(9)]
    issue = make_issue("2026-01-20", picks)
    history = HistoryIndex(album_keys=set(), artist_last_seen={}, style_last_seen={})
    assert validate_today_constraints(issue, history) == []


def test_validator_catches_same_day_duplication_and_cooldowns():
    picks = [make_pick(f"rg-{i}", [f"artist-{i}"], f"style-{i}") for i in range(9)]
    picks[4]["album_key"] = "rg-1"
    picks[5]["artist_keys"] = ["artist-2"]
    picks[6]["style_key"] = "style-1"

    issue = make_issue("2026-01-20", picks)
    history = HistoryIndex(
        album_keys=set(),
        artist_last_seen={"artist-3": "2026-01-14"},
        style_last_seen={"style-7": "2026-01-18"},
    )
    errors = "\n".join(validate_today_constraints(issue, history))
    assert "duplicate album_key" in errors
    assert "duplicate artist" in errors
    assert "duplicate style_key" in errors
    assert "artist cooldown violation" in errors
    assert "style cooldown violation" in errors
