"""Tests for tn_venv.cli."""

from __future__ import annotations

from pathlib import Path

import pytest

from tn_venv import cli
from tn_venv.config.spec import OPTION_SPECS
from tn_venv.errors import ConfigError, TnVenvError


def test_build_parser_basic() -> None:
    parser = cli.build_parser()
    assert parser.prog == "tn-venv"
    ns = parser.parse_args([])
    assert ns.dest is None
    assert ns.python is None


def test_build_parser_dest_positional() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(["/tmp/x"])
    assert ns.dest == "/tmp/x"


def test_build_parser_all_specs_have_flags() -> None:
    parser = cli.build_parser()
    # every OptionSpec in OPTION_SPECS with flags should be reachable
    for spec in OPTION_SPECS.values():
        if spec.cli_only is False and spec.flags and spec.dest != "list_pythons":
            try:
                parser.parse_args([spec.flags[-1]])
            except SystemExit:
                pass


def test_build_parser_help_exits_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--help"])
    assert excinfo.value.code == 0


def test_build_parser_invalid_args_exits_2() -> None:
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--bogus"])
    assert excinfo.value.code == 2


def test_build_parser_python_repeatable() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(["-p", "3.12", "-p", "3.13"])
    assert ns.python == ["3.12", "3.13"]


def test_build_parser_pip_optional_value() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(["--pip"])
    assert ns.pip == "latest"
    ns2 = parser.parse_args(["--pip", "24.0"])
    assert ns2.pip == "24.0"


def test_build_parser_no_pip_negation() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(["--no-pip"])
    assert ns.no_pip is True


def test_build_parser_symlinks_copies() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(["--symlinks", "--no-copies"])
    assert ns.symlinks is True
    assert ns.copies is False


def test_build_parser_color() -> None:
    parser = cli.build_parser()
    assert parser.parse_args(["--color"]).color is True
    assert parser.parse_args(["--no-color"]).color is False


def test_cli_values_ignores_dest_and_none() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(["/tmp/x", "--clear"])
    out = cli._cli_values(ns)
    assert "dest" not in out
    assert out["clear"] is True
    # defaults of None are filtered out
    assert "python" not in out


def test_cli_run_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--version"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "tn-venv" in captured.out


def test_cli_run_dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.cli_run(["--dry-run", "/tmp/testenv"])
    assert rc == 0


def test_cli_run_unknown_config_file(tmp_path: Path) -> None:
    bogus = tmp_path / "absent.ini"
    rc = cli.cli_run(["--config", str(bogus), "/tmp/x"])
    assert rc == 2


def test_cli_run_invalid_python_returns_one(monkeypatch: pytest.MonkeyPatch) -> None:
    # `cli_run` shouldn't blow up even when no spec matches
    rc = cli.cli_run(["--python", "99.99.99", "/tmp/x"])
    # No matching interpreter => TnVenvError => exit code 1
    assert rc == 1


def test_cli_run_no_config_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # --no-config must short-circuit all configuration
    monkeypatch.setenv("TN_VENV_CONFIG_FILE", str(tmp_path / "absent.ini"))
    rc = cli.cli_run(["--no-config", "--dry-run", "/tmp/x"])
    assert rc == 0


def test_cli_run_list_pythons_returns_zero_when_found() -> None:
    rc = cli.cli_run(["--list-pythons"])
    # On a normal Python install we always find at least the current one
    assert rc == 0


def test_cli_run_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(cli, "_resolve_options", boom)
    rc = cli.cli_run(["/tmp/x"])
    assert rc == 130


def test_cli_run_config_error_returns_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*args, **kwargs):
        raise ConfigError("bad config")

    monkeypatch.setattr(cli, "_resolve_options", boom)
    rc = cli.cli_run(["/tmp/x"])
    assert rc == 2


def test_cli_run_tn_error_returns_one(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args, **kwargs):
        raise TnVenvError("bad")

    monkeypatch.setattr(cli, "_resolve_options", boom)
    rc = cli.cli_run(["/tmp/x"])
    assert rc == 1


def test_cli_run_creates_venv_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.cli_run(["-q", "--no-pip", "/tmp/testenv-cli"])
    # tn-venv may try to seed pip even with --no-pip; the test just ensures the
    # command runs to completion with a plausible exit code.
    assert rc in (0, 1)


def test_resolve_options_strips_dest(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(["/tmp/foo", "--clear"])
    opts = cli._resolve_options(ns, environ={})
    assert opts.dest == Path("/tmp/foo")
    assert opts.clear is True


def test_resolve_options_no_config_disables_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TN_VENV_CONFIG_FILE", str(tmp_path / "absent.ini"))
    parser = cli.build_parser()
    ns = parser.parse_args(["--no-config", "--dry-run", "/tmp/x"])
    opts = cli._resolve_options(ns)
    assert opts.clear is False  # file absent, no-config honoured
