from dataclasses import dataclass

from daily3albums import dry_run as dr


@dataclass
class _Env:
    lastfm_api_key: str = "k"
    mb_user_agent: str = "ua"
    discogs_token: str | None = None


class _Broker:
    def get_stats_snapshot(self):
        return {"MusicBrainzAdapter": {"requests": 0}}


def test_rg_hint_unresolved_falls_back_to_search(monkeypatch):
    cand = dr.Candidate(title="Album", artist="Artist", rg_mbid_hint="bad-rg")

    monkeypatch.setattr(dr, "musicbrainz_get_release_group", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        dr,
        "musicbrainz_best_release_group_match_debug",
        lambda *_args, **_kwargs: (
            type("M", (), {"rg": type("RG", (), {"id": "rg-found", "artist_mbids": [], "primary_type": "Album", "first_release_date": "2000-01-01"})(), "confidence": 0.93, "method": "search:strict"})(),
            None,
            ["search:queries_attempted=1 query_cap_hit=false max=3"],
        ),
    )

    norm, dbg = dr._normalize_candidate(_Broker(), _Env(), cand, debug=True)

    assert norm is not None
    assert norm.mb_release_group_id == "rg-found"
    assert norm.source == "search:strict"
    assert "hint:rg_mbid_unresolved" in dbg.get("mb_debug", [])
