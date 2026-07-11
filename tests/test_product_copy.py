from daily3albums.cli import _builtin_min_index_html


def test_builtin_fallback_uses_current_product_name():
    html = _builtin_min_index_html()
    assert "<title>Triangulum Daily</title>" in html
    assert '<h1 style="margin:0;">Triangulum Daily</h1>' in html
    assert "Daily 3 Albums" not in html
