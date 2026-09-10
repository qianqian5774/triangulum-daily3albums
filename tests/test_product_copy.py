from pathlib import Path

from daily3albums.cli import _builtin_min_index_html


ROOT = Path(__file__).resolve().parents[1]


def test_builtin_fallback_uses_current_product_name():
    html = _builtin_min_index_html()
    assert "<title>Triangulum Daily</title>" in html
    assert '<h1 style="margin:0;">Triangulum Daily</h1>' in html
    assert "Daily 3 Albums" not in html


def test_tracked_product_surfaces_use_current_name_and_schedule():
    ambient = (ROOT / "ui" / "src" / "components" / "AmbientOverlay.tsx").read_text(
        encoding="utf-8"
    )
    design_authority = (
        ROOT / "docs" / "design" / "authority" / "ui-redesign-concept-v1.md"
    ).read_text(encoding="utf-8")
    share_template = (
        ROOT / "ui" / "public" / "share" / "share-template-vertical-signal-sheet-1080x1440.svg"
    ).read_text(encoding="utf-8")

    assert "TRIANGULUM DAILY" in ambient
    assert "TRIANGULUM DAILY 3 ALBUMS" not in ambient
    assert "Triangulum Daily" in design_authority
    assert "Triangulum Daily 3 Albums" not in design_authority
    assert "DAILY 3 ALBUMS" not in share_template
    assert [time in share_template for time in ("08:00", "12:30", "16:00")] == [True] * 3
    assert [time in share_template for time in ("06:00", "12:00", "18:00")] == [False] * 3
