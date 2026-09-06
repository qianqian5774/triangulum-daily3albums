from __future__ import annotations

import json
from pathlib import Path

import httpx

from daily3albums.cover_assets import STATIC_COVER_GLOBAL, materialize_static_cover_assets, normalize_cover_url


PNG = b"\x89PNG\r\n\x1a\n" + b"cover-payload"


def _issue(url: str) -> dict:
    return {
        "date": "2026-09-06",
        "slots": [
            {
                "picks": [
                    {
                        "title": "Album",
                        "cover": {"has_cover": True, "optimized_cover_url": url},
                    }
                ]
            }
        ],
    }


def _write_issue(out: Path, url: str) -> Path:
    path = out / "data" / "today.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_issue(url), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_static_cover_assets_cache_remote_images_without_mutating_published_json(tmp_path: Path):
    out = tmp_path / "public"
    source_url = "http://covers.example.test/album.png"
    issue_path = _write_issue(out, source_url)
    before = issue_path.read_bytes()
    requests: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(200, headers={"content-type": "image/png"}, content=PNG)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        summary = materialize_static_cover_assets(
            out,
            cache_dir=tmp_path / "cache",
            client=client,
        )

    canonical_url = normalize_cover_url(source_url)
    manifest_path = out / "assets" / "cover-manifest.js"
    manifest = manifest_path.read_text(encoding="utf-8")
    assert canonical_url == "https://covers.example.test/album.png"
    assert requests == [canonical_url]
    assert summary.total_urls == 1
    assert summary.fetched == 1
    assert summary.cache_hits == 0
    assert summary.failed == 0
    assert STATIC_COVER_GLOBAL in manifest
    assert canonical_url in manifest
    assert len(list((out / "assets" / "covers").glob("*.png"))) == 1
    assert issue_path.read_bytes() == before


def test_static_cover_assets_reuses_cached_file_when_remote_is_unavailable(tmp_path: Path):
    out = tmp_path / "public"
    _write_issue(out, "https://covers.example.test/album.jpg")
    cache = tmp_path / "cache"

    with httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, headers={"content-type": "image/jpeg"}, content=b"\xff\xd8\xffcover"))
    ) as client:
        first = materialize_static_cover_assets(out, cache_dir=cache, client=client)
    assert first.fetched == 1

    with httpx.Client(
        transport=httpx.MockTransport(lambda request: (_ for _ in ()).throw(AssertionError(f"unexpected request: {request.url}")))
    ) as client:
        second = materialize_static_cover_assets(out, cache_dir=cache, client=client)

    assert second.cache_hits == 1
    assert second.fetched == 0
    assert second.failed == 0
    assert len(list((out / "assets" / "covers").glob("*.jpg"))) == 1
