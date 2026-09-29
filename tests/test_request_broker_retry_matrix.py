from pathlib import Path

import httpx
import pytest

from daily3albums.request_broker import (
    BrokerRequestError,
    BrokerResponseError,
    RequestBroker,
    RequestFailed,
)


class _Resp:
    def __init__(self, status_code: int, content: bytes = b"{}"):
        self.status_code = status_code
        self.content = content
        self.headers = {}


def test_broker_retries_5xx_up_to_cap(monkeypatch, tmp_path: Path):
    policies = {
        "hosts": {"example.com": {"rate_limit_rps": 1000, "ttl_default": "1h", "negative_cache_ttl": "1h", "retry": {"max_attempts": 3, "base_delay_ms": 1, "max_delay_ms": 2, "jitter": False}}},
        "adapter_policies": {"A": {"max_retries": 2}},
    }
    broker = RequestBroker(repo_root=tmp_path, endpoint_policies=policies)
    calls = {"n": 0}

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        return _Resp(500)

    monkeypatch.setattr(broker.client, "get", fake_get)
    monkeypatch.setattr("daily3albums.request_broker.time.sleep", lambda *_args, **_kwargs: None)

    with pytest.raises(RequestFailed):
        broker.get("https://example.com/a", adapter_name="A")

    assert calls["n"] == 3
    broker.close()


@pytest.mark.parametrize("status", [429, 503])
def test_transient_http_failure_does_not_poison_persistent_cache(monkeypatch, tmp_path: Path, status: int):
    policies = {
        "hosts": {"example.com": {"rate_limit_rps": 1000, "negative_cache_ttl": "1h"}},
        "adapter_policies": {"A": {"max_retries": 0}},
    }
    url = "https://example.com/album"
    broker = RequestBroker(repo_root=tmp_path, endpoint_policies=policies)
    monkeypatch.setattr(broker.client, "get", lambda *_args, **_kwargs: _Resp(status))
    with pytest.raises(RequestFailed) as caught:
        broker.get(url, adapter_name="A")
    assert caught.value.status == status
    broker.close()

    recovered = RequestBroker(repo_root=tmp_path, endpoint_policies=policies)
    calls = {"n": 0}

    def successful_get(*_args, **_kwargs):
        calls["n"] += 1
        return _Resp(200, b"recovered")

    monkeypatch.setattr(recovered.client, "get", successful_get)
    assert recovered.get(url, adapter_name="A") == b"recovered"
    assert calls["n"] == 1
    monkeypatch.setattr(recovered.client, "get", lambda *_args, **_kwargs: pytest.fail("200 cache missed"))
    assert recovered.get(url, adapter_name="A") == b"recovered"
    recovered.close()


def test_legacy_cached_transient_http_failure_is_refetched(monkeypatch, tmp_path: Path):
    broker = RequestBroker(repo_root=tmp_path, endpoint_policies={})
    url = "https://example.com/album"
    broker._cache_put(broker._cache_key(url), url, 503, {}, b"unavailable", 3600)
    monkeypatch.setattr(broker.client, "get", lambda *_args, **_kwargs: _Resp(200, b"recovered"))
    assert broker.get(url) == b"recovered"
    broker.close()


def test_rate_limit_is_not_treated_as_optional_provider_empty_result(monkeypatch, tmp_path: Path):
    policies = {"adapter_policies": {"DiscogsAdapter": {"fatal_4xx": False, "max_retries": 0}}}
    broker = RequestBroker(repo_root=tmp_path, endpoint_policies=policies)
    monkeypatch.setattr(broker.client, "get", lambda *_args, **_kwargs: _Resp(429))
    with pytest.raises(RequestFailed) as caught:
        broker.get("https://api.discogs.com/search", adapter_name="DiscogsAdapter")
    assert caught.value.code == "rate_limited"
    broker.close()


def test_broker_nonfatal_404_returns_none(monkeypatch, tmp_path: Path):
    policies = {
        "hosts": {"api.discogs.com": {"rate_limit_rps": 1000, "ttl_default": "1h", "negative_cache_ttl": "1h"}},
        "adapter_policies": {"DiscogsAdapter": {"fatal_4xx": False, "treat_404_as_empty": True, "max_retries": 0}},
    }
    broker = RequestBroker(repo_root=tmp_path, endpoint_policies=policies)
    monkeypatch.setattr(broker.client, "get", lambda *args, **kwargs: _Resp(404, b'{"message":"not found"}'))

    out = broker.get("https://api.discogs.com/database/search?q=x", adapter_name="DiscogsAdapter")
    assert out is None
    assert broker.get_last_failure("DiscogsAdapter")["code"] == "provider_not_found"
    monkeypatch.setattr(broker.client, "get", lambda *_args, **_kwargs: pytest.fail("404 cache missed"))
    assert broker.get("https://api.discogs.com/database/search?q=x", adapter_name="DiscogsAdapter") is None
    broker.close()


def test_broker_timeout_retries(monkeypatch, tmp_path: Path):
    policies = {
        "hosts": {"example.com": {"rate_limit_rps": 1000, "ttl_default": "1h", "negative_cache_ttl": "1h", "retry": {"max_attempts": 2, "base_delay_ms": 1, "max_delay_ms": 2, "jitter": False}}},
        "adapter_policies": {"A": {"max_retries": 1}},
    }
    broker = RequestBroker(repo_root=tmp_path, endpoint_policies=policies)
    calls = {"n": 0}

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(broker.client, "get", fake_get)
    monkeypatch.setattr("daily3albums.request_broker.time.sleep", lambda *_args, **_kwargs: None)

    with pytest.raises(BrokerRequestError) as caught:
        broker.get("https://example.com/a", adapter_name="A")

    assert calls["n"] == 2
    assert caught.value.code == "timeout"
    broker.close()


def test_broker_redacts_query_and_raw_exception_text(tmp_path: Path, monkeypatch):
    policies = {
        "hosts": {"example.com": {"rate_limit_rps": 1000, "ttl_default": "1h", "negative_cache_ttl": "1h"}},
        "adapter_policies": {"A": {"max_retries": 0}},
    }
    broker = RequestBroker(repo_root=tmp_path, endpoint_policies=policies)
    monkeypatch.setattr(broker.client, "get", lambda *_args, **_kwargs: _Resp(200, b"not-json"))

    with pytest.raises(BrokerResponseError) as caught:
        broker.get_json(
            "https://example.com/data?api_key=super-secret&token=also-secret&q=ambient",
            adapter_name="A",
        )

    message = str(caught.value)
    assert caught.value.code == "corrupt"
    assert "super-secret" not in message
    assert "also-secret" not in message
    assert "not-json" not in message
    assert "api_key=%2A%2A%2A" in message
    broker.close()
