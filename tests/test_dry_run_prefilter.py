from dataclasses import dataclass

from daily3albums.adapters import LastFmTopAlbum
from daily3albums import dry_run as dr


@dataclass
class _Env:
    lastfm_api_key: str = "k"
    mb_user_agent: str = "ua"
    discogs_token: str | None = None


class _Broker:
    pass


def _make_albums(n: int) -> list[LastFmTopAlbum]:
    out = []
    for i in range(1, n + 1):
        out.append(
            LastFmTopAlbum(
                name=f"Album {i}",
                artist=f"Artist {i}",
                mbid=f"mbid-{i}",
                playcount=None,
                url=None,
                rank=i,
                image_extralarge=None,
            )
        )
    return out


def test_run_dry_run_prefilter_caps_normalization(monkeypatch):
    monkeypatch.setattr(dr, "lastfm_tag_top_albums", lambda *args, **kwargs: _make_albums(200))
    monkeypatch.setattr(dr, "listenbrainz_sitewide_release_groups", lambda *args, **kwargs: [])

    calls = {"n": 0}

    def fake_norm(_broker, _env, c, debug=False):
        calls["n"] += 1
        return (
            dr.NormalizedCandidate(
                title=c.title,
                artist=c.artist,
                mb_release_group_id=f"rg-{c.title}",
                artist_mbids=[],
            ),
            {"mb_debug": []},
        )

    monkeypatch.setattr(dr, "_normalize_candidate", fake_norm)

    out = dr.run_dry_run(_Broker(), _Env(), tag="ambient", n=200, topk=200, seed_key="s", prefilter_topn=120)

    assert calls["n"] <= 120
    assert out["normalized_count"] == 120
    assert out["prefilter_topn"] == 120


def test_run_dry_run_prefilter_is_deterministic(monkeypatch):
    monkeypatch.setattr(dr, "lastfm_tag_top_albums", lambda *args, **kwargs: _make_albums(150))
    monkeypatch.setattr(dr, "listenbrainz_sitewide_release_groups", lambda *args, **kwargs: [])

    def fake_norm(_broker, _env, c, debug=False):
        return (
            dr.NormalizedCandidate(
                title=c.title,
                artist=c.artist,
                mb_release_group_id=f"rg-{c.title}",
                artist_mbids=[],
            ),
            {"mb_debug": []},
        )

    monkeypatch.setattr(dr, "_normalize_candidate", fake_norm)

    out1 = dr.run_dry_run(_Broker(), _Env(), tag="ambient", n=150, topk=50, seed_key="d:0:ambient", prefilter_topn=80)
    out2 = dr.run_dry_run(_Broker(), _Env(), tag="ambient", n=150, topk=50, seed_key="d:0:ambient", prefilter_topn=80)

    top1 = [(x.c.artist, x.c.title, round(float(x.score), 6)) for x in out1["top"]]
    top2 = [(x.c.artist, x.c.title, round(float(x.score), 6)) for x in out2["top"]]
    assert top1 == top2
