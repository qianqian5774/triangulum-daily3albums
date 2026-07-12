import sys

import pytest

from daily3albums import cli


def test_cli_help_excludes_retired_doctor(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["daily3albums", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "doctor" not in output.lower()
    for command in ("probe-lastfm", "probe-mb", "dry-run", "build"):
        assert command in output
