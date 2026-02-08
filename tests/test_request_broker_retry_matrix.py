from pathlib import Path

import httpx
import pytest

from daily3albums.request_broker import RequestBroker, RequestFailed


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


def test_broker_nonfatal_404_returns_none(monkeypatch, tmp_path: Path):
    policies = {
        "hosts": {"api.discogs.com": {"rate_limit_rps": 1000, "ttl_default": "1h", "negative_cache_ttl": "1h"}},
        "adapter_policies": {"DiscogsAdapter": {"fatal_4xx": False, "treat_404_as_empty": True, "max_retries": 0}},
    }
    broker = RequestBroker(repo_root=tmp_path, endpoint_policies=policies)
    monkeypatch.setattr(broker.client, "get", lambda *args, **kwargs: _Resp(404, b'{"message":"not found"}'))

    out = broker.get("https://api.discogs.com/database/search?q=x", adapter_name="DiscogsAdapter")
    assert out is None
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

    with pytest.raises(Exception):
        broker.get("https://example.com/a", adapter_name="A")

    assert calls["n"] == 2
    broker.close()
