from __future__ import annotations

from scripts.self_check import _scan_for_legacy_project_site_paths


def test_scan_for_legacy_project_site_paths_rejects_old_pages_url(tmp_path):
    public_js = tmp_path / "assets" / "app.js"
    public_js.parent.mkdir()
    legacy_url = "https://qianqian5774.github.io/triangulum-daily3albums/data/today.json"
    public_js.write_text(
        f'fetch("{legacy_url}")',
        encoding="utf-8",
    )

    problems = _scan_for_legacy_project_site_paths([public_js])

    assert problems == [f"Legacy GitHub Pages project-site path detected in {public_js}"]


def test_scan_for_legacy_project_site_paths_allows_repository_links(tmp_path):
    public_js = tmp_path / "assets" / "app.js"
    public_js.parent.mkdir()
    public_js.write_text(
        'const repo = "https://github.com/qianqian5774/triangulum-daily3albums";',
        encoding="utf-8",
    )

    assert _scan_for_legacy_project_site_paths([public_js]) == []
