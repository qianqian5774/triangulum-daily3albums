from pathlib import Path

import httpx

from daily3albums import cli
from daily3albums.adapters import ProviderApiError, lastfm_tag_top_albums
from daily3albums.request_broker import BrokerRequestError


class _LastfmApplicationErrorBroker:
    def get_json(self, *args, **kwargs):
        return {"error": 29, "message": "Rate Limit Exceeded"}


def test_doctor_output_is_explicitly_basic_not_e2e(capsys):
    repo_root = Path(__file__).resolve().parents[1]

    rc = cli.cmd_doctor(repo_root)

    assert rc == 0
    out = capsys.readouterr().out
    assert "doctor_scope=basic_not_e2e" in out
    assert "checked=config/env loading, timezone, CLI basics" in out
    assert "not_checked=UI render, archive route, detail route, network probes" in out
    assert "not a full end-to-end health signal" in out


def test_lastfm_application_error_has_provider_stage_and_advice():
    try:
        lastfm_tag_top_albums(
            _LastfmApplicationErrorBroker(),
            lastfm_api_key="k",
            tag="ambient",
            limit=50,
            page=1,
        )
    except ProviderApiError as exc:
        message = str(exc)
    else:
        raise AssertionError("Last.fm application error should raise ProviderApiError")

    assert "provider=Last.fm" in message
    assert "stage=tag.getTopAlbums" in message
    assert "Rate Limit Exceeded" in message
    assert "LASTFM_API_KEY" in message


def test_musicbrainz_timeout_failure_message_names_context():
    err = BrokerRequestError(
        adapter_name="MusicBrainzAdapter",
        url="https://musicbrainz.org/ws/2/release-group?fmt=json",
        cause=httpx.ReadTimeout("timed out"),
    )

    message = cli._format_external_api_failure(
        slot_id=1,
        tag="cool jazz",
        stage="candidate_fetch",
        exc=err,
        fetch_limit=200,
    )

    assert "provider=MusicBrainz" in message
    assert "slot=1" in message
    assert 'tag="cool jazz"' in message
    assert "stage=musicbrainz_normalize" in message
    assert "ReadTimeout" in message
    assert "MB_USER_AGENT" in message


def test_candidate_pool_exhaustion_message_is_actionable():
    message = cli._format_slot_exhaustion_failure(
        {
            "slot_id": 2,
            "tag_attempts": [
                {
                    "tag": "free jazz",
                    "candidate_count": 2,
                    "candidate_count_after_hard_filters": 1,
                    "reject_counts": {"artist_cooldown": 1},
                },
                {
                    "tag": "spiritual jazz",
                    "network_failed": True,
                    "error": "provider=MusicBrainz stage=musicbrainz_normalize error=timeout",
                },
            ],
            "top_rejection_reasons": [["artist_cooldown", 1]],
        }
    )

    assert "candidate_pool_exhausted" in message
    assert "provider=candidate_pool" in message
    assert "slot=2" in message
    assert "stage=slot_selection" in message
    assert "spiritual jazz" in message
    assert "artist_cooldown" in message
    assert "advice=" in message
