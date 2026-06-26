from types import SimpleNamespace

from daily3albums.cli import _pick_to_issue_item


def test_cover_policy_allows_placeholder_when_no_cover_source_available():
    scored = SimpleNamespace(
        c=SimpleNamespace(title="No Cover Album", artist="No Cover Artist", image_url=""),
        n=SimpleNamespace(
            mb_release_group_id="rg-no-cover",
            first_release_date="2001-01-01",
            primary_type="Album",
            artist_mbids=["artist-no-cover"],
            confidence=0.91,
        ),
        score=10.0,
        reason="fixture",
    )

    item = _pick_to_issue_item(tag="fixture", slot="Headliner", s=scored, cover_result=None)

    assert item["cover"]["has_cover"] is False
    assert item["cover"]["optimized_cover_url"] == "assets/placeholder.svg"
    assert item["cover"]["original_cover_url"] is None


def test_pick_item_includes_musicbrainz_details_when_available():
    scored = SimpleNamespace(
        c=SimpleNamespace(title="Album", artist="Artist", image_url=""),
        n=SimpleNamespace(
            mb_release_group_id="rg",
            first_release_date="2001-01-01",
            primary_type="Album",
            artist_mbids=["artist"],
            confidence=0.91,
        ),
        score=10.0,
        reason="fixture",
    )
    details = SimpleNamespace(
        rating_value=4.2,
        rating_votes_count=12,
        tags=[{"name": "punk", "source": "musicbrainz", "count": 4}],
        wikipedia_url="https://en.wikipedia.org/wiki/Album",
    )
    overview = {
        "text": "Album overview.",
        "source": "wikipedia",
        "source_url": "https://en.wikipedia.org/wiki/Album",
        "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
    }

    item = _pick_to_issue_item(
        tag="fixture",
        slot="Headliner",
        s=scored,
        cover_result=None,
        mb_details=details,
        wikipedia_overview=overview,
    )

    assert item["musicbrainz"]["rating"] == {"value": 4.2, "votes_count": 12}
    assert item["musicbrainz"]["tags"] == [{"name": "punk", "source": "musicbrainz", "count": 4}]
    assert item["musicbrainz"]["overview"]["text"] == "Album overview."
    assert item["tags"] == [{"name": "fixture", "source": "lastfm"}, {"name": "punk", "source": "musicbrainz", "count": 4}]
