from dataclasses import dataclass
from pathlib import Path

from daily3albums.adapters import DiscogsSearchItem, LastFmTopAlbum
from daily3albums import dry_run as dr
from daily3albums.request_broker import RequestBroker


@dataclass
class _Env:
    lastfm_api_key: str = "k"
    mb_user_agent: str = "ua"
    discogs_token: str | None = "discogs-token"


def test_discogs_cached_404_nonfatal_returns_empty(tmp_path: Path):
    policies = {
        "hosts": {"api.discogs.com": {"ttl_default": "1h", "negative_cache_ttl": "1h", "rate_limit_rps": 100}},
        "adapter_policies": {
            "DiscogsAdapter": {
                "fatal_4xx": False,
                "treat_404_as_empty": True,
                "negative_cache_ttl_s": 600,
                "max_pages": 3,
            }
        },
    }
    broker = RequestBroker(repo_root=tmp_path, endpoint_policies=policies)
    try:
        url = "https://api.discogs.com/database/search?q=electronic&type=master&format=album&page=3&per_page=100"
        key = broker._cache_key(url)
        broker._cache_put(key, url, 404, {}, b'{"message":"not found"}', ttl_s=3600)

        items = dr.discogs_database_search(
            broker,
            "token",
            q="electronic",
            page=3,
            per_page=100,
        )
        assert items == []
        diag = getattr(broker, "_discogs_last_diagnostics", {})
        assert diag.get("discogs_failed") is True
        assert diag.get("discogs_failed_status") == 404
    finally:
        broker.close()


def test_run_dry_run_tolerates_discogs_runtime_error(monkeypatch):
    monkeypatch.setattr(
        dr,
        "lastfm_tag_top_albums",
        lambda *args, **kwargs: [
            LastFmTopAlbum("A", "B", "m1", None, None, 1, None),
            LastFmTopAlbum("C", "D", "m2", None, None, 2, None),
        ],
    )
    monkeypatch.setattr(dr, "listenbrainz_sitewide_release_groups", lambda *args, **kwargs: [])
    monkeypatch.setattr(dr, "listenbrainz_metadata_release_groups", lambda *args, **kwargs: {})

    def fake_norm(_broker, _env, c, debug=False, mb_search_limit=10, mb_max_queries_per_candidate=3):
        return (
            dr.NormalizedCandidate(title=c.title, artist=c.artist, mb_release_group_id=f"rg-{c.title}"),
            {"mb_debug": [], "mb_queries_attempted": 0},
        )

    monkeypatch.setattr(dr, "_normalize_candidate", fake_norm)
    monkeypatch.setattr(dr, "discogs_database_search", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("HTTP 404 cached")))

    out = dr.run_dry_run(_Broker(), _Env(), tag="electronic", n=20, topk=10)
    assert "top" in out
    assert out.get("discogs_failed") is True


def test_discogs_paging_cap(monkeypatch):
    calls = {"page": None}

    def fake_discogs(_broker, _token, *, q, page=1, per_page=100, type_="master", format_="album"):
        calls["page"] = page
        return []

    monkeypatch.setattr(dr, "discogs_database_search", fake_discogs)
    monkeypatch.setattr(dr, "lastfm_tag_top_albums", lambda *args, **kwargs: [])
    monkeypatch.setattr(dr, "listenbrainz_sitewide_release_groups", lambda *args, **kwargs: [])

    out = dr.run_dry_run(
        _Broker(),
        _Env(),
        tag="electronic",
        n=20,
        topk=10,
        deepcut=True,
        seed_key="forcehigh",
        discogs_page_start=7,
        discogs_max_pages=2,
    )

    assert calls["page"] == 2
    assert out.get("discogs_page_cap_hit") is True


class _Broker:
    pass
