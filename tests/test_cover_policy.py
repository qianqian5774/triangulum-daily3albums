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
