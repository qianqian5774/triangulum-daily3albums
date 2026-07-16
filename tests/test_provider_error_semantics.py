from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from daily3albums import cli, dry_run as dr
from daily3albums.adapters import (
    CoverArtArchiveAdapter,
    LastFmTopAlbum,
    ProviderApiError,
    discogs_database_search_result,
    listenbrainz_sitewide_release_groups_result,
    musicbrainz_get_release_group_details_result,
)
from daily3albums.request_broker import BrokerRequestError, RequestFailed
from daily3albums.runtime_outcomes import OutcomeCode, RuntimeOutcome


class _ResponseBroker:
    def __init__(self, response=None, error: Exception | None = None, last_failure=None):
        self.response = response
        self.error = error
        self.last_failure = last_failure

    def get_json(self, *_args, **_kwargs):
        if self.error is not None:
            raise self.error
        return self.response

    def get_last_failure(self, _adapter):
        return self.last_failure


@pytest.mark.parametrize(
    ("response", "error", "expected"),
    [
        ({"results": []}, None, OutcomeCode.LEGITIMATE_EMPTY),
        ({"results": "wrong"}, None, OutcomeCode.CORRUPT),
        (None, RequestFailed("DiscogsAdapter", "https://api.discogs.com", 404), OutcomeCode.PROVIDER_NOT_FOUND),
        (
            None,
            BrokerRequestError("DiscogsAdapter", "https://api.discogs.com", httpx.ConnectError("offline")),
            OutcomeCode.REQUEST_FAILED,
        ),
        (
            None,
            BrokerRequestError("DiscogsAdapter", "https://api.discogs.com", httpx.ReadTimeout("late")),
            OutcomeCode.TIMEOUT,
        ),
    ],
)
def test_discogs_adapter_maps_stable_outcomes(response, error, expected):
    result = discogs_database_search_result(_ResponseBroker(response, error), "token", q="ambient")

    assert result.value == []
    assert result.outcome.code == expected


@pytest.mark.parametrize(
    ("response", "error", "expected"),
    [
        ({"release_groups": []}, None, OutcomeCode.LEGITIMATE_EMPTY),
        ({"release_groups": "wrong"}, None, OutcomeCode.CORRUPT),
        (
            None,
            BrokerRequestError("ListenBrainzAdapter", "https://api.listenbrainz.org", httpx.ConnectError("offline")),
            OutcomeCode.REQUEST_FAILED,
        ),
        (
            None,
            BrokerRequestError("ListenBrainzAdapter", "https://api.listenbrainz.org", httpx.ReadTimeout("late")),
            OutcomeCode.TIMEOUT,
        ),
    ],
)
def test_listenbrainz_adapter_maps_stable_outcomes(response, error, expected):
    result = listenbrainz_sitewide_release_groups_result(_ResponseBroker(response, error))

    assert result.value == []
    assert result.outcome.code == expected


def test_musicbrainz_detail_and_cover_keep_missing_distinct_from_request_failure_and_timeout():
    missing_broker = _ResponseBroker(None, last_failure={"status": 404, "code": "provider_not_found"})
    request_failure = BrokerRequestError(
        "MusicBrainzAdapter",
        "https://musicbrainz.org/ws/2/release-group/id?fmt=json",
        httpx.ConnectError("offline"),
    )
    timeout = BrokerRequestError(
        "MusicBrainzAdapter",
        "https://musicbrainz.org/ws/2/release-group/id?fmt=json",
        httpx.ReadTimeout("late"),
    )

    missing_detail = musicbrainz_get_release_group_details_result(missing_broker, "ua", "rg-id")
    failed_detail = musicbrainz_get_release_group_details_result(
        _ResponseBroker(error=request_failure), "ua", "rg-id"
    )
    timeout_detail = musicbrainz_get_release_group_details_result(_ResponseBroker(error=timeout), "ua", "rg-id")
    missing_cover = CoverArtArchiveAdapter(missing_broker).fetch_cover_result("rg-id")
    failed_cover = CoverArtArchiveAdapter(_ResponseBroker(error=request_failure)).fetch_cover_result("rg-id")
    timeout_cover = CoverArtArchiveAdapter(_ResponseBroker(error=timeout)).fetch_cover_result("rg-id")

    assert missing_detail.outcome.code == OutcomeCode.PROVIDER_NOT_FOUND
    assert failed_detail.outcome.code == OutcomeCode.REQUEST_FAILED
    assert timeout_detail.outcome.code == OutcomeCode.TIMEOUT
    assert missing_cover.outcome.code == OutcomeCode.PROVIDER_NOT_FOUND
    assert failed_cover.outcome.code == OutcomeCode.REQUEST_FAILED
    assert timeout_cover.outcome.code == OutcomeCode.TIMEOUT


def test_wikipedia_relation_summary_request_failure_and_timeout_have_distinct_outcomes():
    relation_missing = cli._wikipedia_overview_result(_ResponseBroker({}), None, "ua", lambda _line: None)
    summary_missing = cli._wikipedia_overview_result(
        _ResponseBroker({"extract": ""}),
        "https://en.wikipedia.org/wiki/Album",
        "ua",
        lambda _line: None,
    )
    request_failure = cli._wikipedia_overview_result(
        _ResponseBroker(
            error=BrokerRequestError(
                "WikipediaAdapter",
                "https://en.wikipedia.org/api/rest_v1/page/summary/Album",
                httpx.ConnectError("offline"),
            )
        ),
        "https://en.wikipedia.org/wiki/Album",
        "ua",
        lambda _line: None,
    )
    timeout = cli._wikipedia_overview_result(
        _ResponseBroker(
            error=BrokerRequestError(
                "WikipediaAdapter",
                "https://en.wikipedia.org/api/rest_v1/page/summary/Album",
                httpx.ReadTimeout("late"),
            )
        ),
        "https://en.wikipedia.org/wiki/Album",
        "ua",
        lambda _line: None,
    )

    assert relation_missing.outcome.code == OutcomeCode.MISSING
    assert relation_missing.outcome.resource == "wikipedia_relation"
    assert summary_missing.outcome.code == OutcomeCode.MISSING
    assert summary_missing.outcome.resource == "wikipedia_summary"
    assert request_failure.outcome.code == OutcomeCode.REQUEST_FAILED
    assert timeout.outcome.code == OutcomeCode.TIMEOUT


@dataclass
class _Env:
    lastfm_api_key: str = "key"
    mb_user_agent: str = "ua"
    discogs_token: str | None = "token"


class _SoftBroker:
    pass


def _install_primary_funnel(monkeypatch):
    monkeypatch.setattr(
        dr,
        "lastfm_tag_top_albums",
        lambda *_args, **_kwargs: [
            LastFmTopAlbum("A", "Artist A", None, None, None, 1, None),
            LastFmTopAlbum("B", "Artist B", None, None, None, 2, None),
            LastFmTopAlbum("C", "Artist C", None, None, None, 3, None),
        ],
    )

    def normalize(_broker, _env, candidate, **_kwargs):
        return (
            dr.NormalizedCandidate(
                title=candidate.title,
                artist=candidate.artist,
                mb_release_group_id=f"rg-{candidate.title}",
            ),
            {"mb_debug": [], "mb_queries_attempted": 0},
        )

    monkeypatch.setattr(dr, "_normalize_candidate", normalize)


def _top_titles(out):
    return [item.c.title for item in out["top"]]


def test_discogs_disabled_not_configured_empty_and_failures_do_not_change_primary_funnel(monkeypatch):
    _install_primary_funnel(monkeypatch)
    monkeypatch.setattr(dr, "listenbrainz_sitewide_release_groups", lambda *_args, **_kwargs: [])
    baseline = dr.run_dry_run(
        _SoftBroker(),
        _Env(),
        tag="ambient",
        n=20,
        topk=10,
        discogs_enabled=False,
    )
    expected = _top_titles(baseline)
    assert baseline["discogs_outcome_code"] == "disabled"

    not_configured = dr.run_dry_run(
        _SoftBroker(),
        _Env(discogs_token=None),
        tag="ambient",
        n=20,
        topk=10,
    )
    assert not_configured["discogs_outcome_code"] == "not_configured"
    assert _top_titles(not_configured) == expected

    def empty_discogs(broker, *_args, **_kwargs):
        broker._discogs_last_diagnostics = {
            "discogs_failed": False,
            "discogs_failed_status": None,
            "discogs_cached_negative_used": False,
            "discogs_page_cap_hit": False,
            "discogs_pages_fetched": 1,
            "discogs_outcome_code": "legitimate_empty",
        }
        return []

    monkeypatch.setattr(dr, "discogs_database_search", empty_discogs)
    empty = dr.run_dry_run(_SoftBroker(), _Env(), tag="ambient", n=20, topk=10)
    assert empty["discogs_outcome_code"] == "legitimate_empty"
    assert _top_titles(empty) == expected

    for cause, code in [
        (httpx.ConnectError("offline"), "request_failed"),
        (httpx.ReadTimeout("late"), "timeout"),
    ]:
        monkeypatch.setattr(
            dr,
            "discogs_database_search",
            lambda *_args, _cause=cause, **_kwargs: (_ for _ in ()).throw(
                BrokerRequestError("DiscogsAdapter", "https://api.discogs.com", _cause)
            ),
        )
        failed = dr.run_dry_run(_SoftBroker(), _Env(), tag="ambient", n=20, topk=10)
        assert failed["discogs_outcome_code"] == code
        assert failed["discogs_failed"] is True
        assert _top_titles(failed) == expected


@pytest.mark.parametrize(
    ("cause", "expected_code"),
    [
        (httpx.ConnectError("offline"), "request_failed"),
        (httpx.ReadTimeout("late"), "timeout"),
    ],
)
def test_listenbrainz_failures_do_not_change_primary_funnel(monkeypatch, cause, expected_code):
    _install_primary_funnel(monkeypatch)
    monkeypatch.setattr(dr, "discogs_database_search", lambda *_args, **_kwargs: [])
    baseline = dr.run_dry_run(
        _SoftBroker(),
        _Env(),
        tag="ambient",
        n=20,
        topk=10,
        lastfm_only=True,
    )
    monkeypatch.setattr(
        dr,
        "listenbrainz_sitewide_release_groups",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            BrokerRequestError("ListenBrainzAdapter", "https://api.listenbrainz.org", cause)
        ),
    )
    failed = dr.run_dry_run(
        _SoftBroker(),
        _Env(),
        tag="ambient",
        n=20,
        topk=10,
        discogs_enabled=False,
    )

    assert failed["listenbrainz_outcome_code"] == expected_code
    assert failed["listenbrainz_failed"] is True
    assert _top_titles(failed) == _top_titles(baseline)


def test_runtime_outcome_code_is_independent_of_raw_exception_message():
    first = BrokerRequestError("MusicBrainzAdapter", "https://musicbrainz.org", httpx.ReadTimeout("alpha"))
    second = BrokerRequestError("MusicBrainzAdapter", "https://musicbrainz.org", httpx.ReadTimeout("beta"))

    assert first.code == second.code == "timeout"
    assert "alpha" not in str(first)
    assert "beta" not in str(second)


def test_missing_provider_config_has_structured_not_configured_code():
    with pytest.raises(ProviderApiError) as exc_info:
        dr.run_dry_run(
            _SoftBroker(),
            _Env(lastfm_api_key=""),
            tag="ambient",
            n=20,
            topk=10,
        )

    assert exc_info.value.code == OutcomeCode.NOT_CONFIGURED.value
    assert exc_info.value.provider == "Last.fm"
    assert exc_info.value.stage == "config_check"


def test_unclassified_programming_error_is_not_mislabeled_as_provider_failure():
    with pytest.raises(ValueError, match="programming bug"):
        listenbrainz_sitewide_release_groups_result(
            _ResponseBroker(error=ValueError("programming bug"))
        )
