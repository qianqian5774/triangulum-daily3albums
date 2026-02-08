from pathlib import Path

from daily3albums.config import load_config


def test_load_config_defaults_decade_mode_off_and_ignores_legacy_keys(tmp_path: Path):
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "endpoint_policies.yaml").write_text("{}\n", encoding="utf-8")
    (tmp_path / "config" / "config.yaml").write_text(
        """
        timezone: Asia/Shanghai
        build:
          min_in_decade: 6
          max_unknown_year: 2
        decade_axis: 1990s
        """,
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)
    assert cfg.decade_mode == "off"
    assert set(cfg.ignored_legacy_decade_keys) == {"min_in_decade", "max_unknown_year", "decade_axis"}
