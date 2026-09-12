"""Tests for tn_venv.config.loader."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tn_venv.config.loader import (
    find_default_config,
    load_env_config,
    load_file_config,
)
from tn_venv.errors import ConfigError


def test_load_env_returns_empty_when_nothing_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in list(os.environ):
        if key.startswith("TN_VENV_"):
            monkeypatch.delenv(key, raising=False)
    assert load_env_config({}) == {}


def test_load_env_bool_coercion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TN_VENV_CLEAR", "yes")
    monkeypatch.setenv("TN_VENV_NO_PIP", "1")
    out = load_env_config()
    assert out["clear"] is True
    assert out["no_pip"] is True


def test_load_env_ignores_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TN_VENV_BOGUS", "x")
    monkeypatch.delenv("TN_VENV_CLEAR", raising=False)
    out = load_env_config()
    assert "bogus" not in out


def test_load_env_append_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TN_VENV_PYTHON", "3.12,3.13")
    out = load_env_config()
    assert out["python"] == ["3.12", "3.13"]


def test_load_env_invalid_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TN_VENV_SEEDER", "bogus")
    with pytest.raises(ConfigError):
        load_env_config()


def test_load_file_returns_none_when_path_is_none(tmp_path: Path) -> None:
    assert load_file_config(None) == {}


def test_load_file_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_file_config(tmp_path / "missing.ini")


def test_load_file_ini(tmp_path: Path) -> None:
    ini = tmp_path / "tn-venv.ini"
    ini.write_text(
        "[tn-venv]\nclear = yes\nprompt = myproj\npython = 3.12, 3.13\n",
        encoding="utf-8",
    )
    out = load_file_config(ini)
    assert out["clear"] is True
    assert out["prompt"] == "myproj"
    assert out["python"] == ["3.12", "3.13"]


def test_load_file_ini_underscore_keys(tmp_path: Path) -> None:
    ini = tmp_path / "tn-venv.ini"
    ini.write_text(
        "[tn-venv]\nextra_search_dir = /tmp/wheels,/var/cache\nno_pip = true\n",
        encoding="utf-8",
    )
    out = load_file_config(ini)
    assert out["extra_search_dir"] == ["/tmp/wheels", "/var/cache"]
    assert out["no_pip"] is True


def test_load_file_pyproject(tmp_path: Path) -> None:
    pp = tmp_path / "pyproject.toml"
    pp.write_text(
        '[project]\nname = "x"\n\n[tool.tn-venv]\nclear = true\nprompt = "myproj"\n',
        encoding="utf-8",
    )
    out = load_file_config(pp)
    assert out["clear"] is True
    assert out["prompt"] == "myproj"


def test_load_file_pyproject_underscore_section(tmp_path: Path) -> None:
    pp = tmp_path / "pyproject.toml"
    pp.write_text(
        '[project]\nname = "x"\n\n[tool.tn_venv]\nclear = false\n',
        encoding="utf-8",
    )
    out = load_file_config(pp)
    assert out["clear"] is False


def test_load_file_pyproject_invalid_raises(tmp_path: Path) -> None:
    pp = tmp_path / "pyproject.toml"
    pp.write_text("this is = not valid [toml", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_file_config(pp)


def test_load_file_dedicated_toml(tmp_path: Path) -> None:
    cfg = tmp_path / ".tn-venv.toml"
    cfg.write_text('prompt = "dedicated"\nclear = true\n', encoding="utf-8")
    out = load_file_config(cfg)
    assert out["prompt"] == "dedicated"
    assert out["clear"] is True


def test_load_file_ignores_unknown_keys(tmp_path: Path) -> None:
    ini = tmp_path / "tn-venv.ini"
    ini.write_text(
        "[tn-venv]\nbogus_option = whatever\nclear = true\n", encoding="utf-8"
    )
    out = load_file_config(ini)
    assert "bogus_option" not in out
    assert out["clear"] is True


def test_load_file_setup_cfg(tmp_path: Path) -> None:
    cfg = tmp_path / "setup.cfg"
    cfg.write_text(
        "[tn_venv]\nclear = true\nprompt = via_setup_cfg\n", encoding="utf-8"
    )
    out = load_file_config(cfg)
    assert out["clear"] is True
    assert out["prompt"] == "via_setup_cfg"


def test_find_default_config_stops_at_git(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    parent = tmp_path.parent
    ini = parent / "tn-venv.ini"
    ini.write_text("[tn-venv]\nclear = true\n", encoding="utf-8")
    try:
        assert find_default_config(tmp_path) is None
    finally:
        ini.unlink()


def test_find_default_config_picks_pyproject_with_section(tmp_path: Path) -> None:
    pp = tmp_path / "pyproject.toml"
    pp.write_text(
        '[project]\nname = "x"\n\n[tool.tn-venv]\nclear = true\n',
        encoding="utf-8",
    )
    assert find_default_config(tmp_path) == pp


def test_find_default_config_picks_tn_venv_ini(tmp_path: Path) -> None:
    ini = tmp_path / "tn-venv.ini"
    ini.write_text("[tn-venv]\n", encoding="utf-8")
    assert find_default_config(tmp_path) == ini


def test_find_default_config_picks_pyproject_without_section(tmp_path: Path) -> None:
    pp = tmp_path / "pyproject.toml"
    pp.write_text("[project]\nname = 'x'\n", encoding="utf-8")
    assert find_default_config(tmp_path) is None
