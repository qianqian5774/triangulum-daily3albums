from dataclasses import dataclass

from daily3albums.adapters import LastFmTopAlbum
from daily3albums import dry_run as dr


@dataclass
class _Env:
    lastfm_api_key: str = "k"
    mb_user_agent: str = "ua"
    discogs_token: str | None = None


class _Broker:
    def __init__(self):
        self.calls = 0

    def get_stats_snapshot(self):
        return {"MusicBrainzAdapter": {"requests": self.calls}}


def test_mb_diagnostics_split_http_vs_search(monkeypatch):
    broker = _Broker()
    monkeypatch.setattr(
        dr,
        "lastfm_tag_top_albums",
        lambda *args, **kwargs: [LastFmTopAlbum("A", "B", None, None, None, 1, None)],
    )
    monkeypatch.setattr(dr, "listenbrainz_sitewide_release_groups", lambda *args, **kwargs: [])

    def fake_match(*args, **kwargs):
        broker.calls += 2
        match = type("M", (), {"rg": type("RG", (), {"id": "rg1", "artist_mbids": [], "primary_type": "Album", "first_release_date": "2001-01-01"})(), "confidence": 0.9, "method": "search:strict"})()
        return match, None, ["search:queries_attempted=1 query_cap_hit=false max=3"]

    monkeypatch.setattr(dr, "musicbrainz_best_release_group_match_debug", fake_match)

    out = dr.run_dry_run(
        broker,
        _Env(),
        tag="ambient",
        n=1,
        topk=1,
        prefilter_topn=1,
        mb_max_candidates_per_slot=1,
    )

    assert out["mb_search_queries_attempted_total"] == 1
    assert out["mb_http_calls_total"] == 2
    assert out["mb_queries_attempted_total"] == 2
