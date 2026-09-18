"""Tests for tn_venv.create_venv — the high-level create helper."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tn_venv.discovery import PythonInfo
from tn_venv.errors import TnVenvError
from tn_venv.session import SessionResult, create_venv


def test_create_venv_basic(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    result = create_venv(dest, quiet=True)
    assert isinstance(result, SessionResult)
    assert result.env_dir == dest
    assert dest.exists()
    assert (dest / "pyvenv.cfg").is_file()


def test_create_venv_no_pip(tmp_path: Path) -> None:
    dest = tmp_path / "venv-nopip"
    create_venv(dest, with_pip=False, quiet=True)
    assert dest.exists()


def test_create_venv_existing_raises(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    create_venv(dest, quiet=True)
    with pytest.raises(TnVenvError):
        create_venv(dest, quiet=True)


def test_create_venv_clear_existing(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    create_venv(dest, quiet=True)
    result = create_venv(dest, clear=True, quiet=True)
    assert result.env_dir == dest


def test_create_venv_default_activators(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    result = create_venv(dest, quiet=True)
    assert isinstance(result.activation_scripts, list)


def test_create_venv_chosen_activator(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    create_venv(dest, activators=["bash"], quiet=True)
    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    assert (dest / bin_dir / "activate").exists()


def test_create_venv_prompt(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    create_venv(dest, prompt="myproj", quiet=True)
    cfg = (dest / "pyvenv.cfg").read_text(encoding="utf-8")
    assert "myproj" in cfg


def test_create_venv_system_site_packages(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    create_venv(dest, system_site_packages=True, quiet=True)
    cfg = (dest / "pyvenv.cfg").read_text(encoding="utf-8")
    assert "true" in cfg.lower()


def test_create_venv_setuptools_and_wheel_bool(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    create_venv(dest, setuptools=True, wheel=True, quiet=True)
    assert dest.exists()


def test_create_venv_setuptools_and_wheel_pinned(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    create_venv(dest, setuptools="80.0.0", wheel="0.43.0", quiet=True)
    assert dest.exists()


def test_create_venv_python_string_spec(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    create_venv(dest, python="3", quiet=True)
    assert (dest / "pyvenv.cfg").is_file()


def test_create_venv_invalid_python_raises(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    with pytest.raises(TnVenvError):
        create_venv(dest, python="99.99.99", quiet=True)


def test_create_venv_unexpected_failure_wrapped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tn_venv import session

    def boom(options, reporter=None):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(session, "run_session", boom)
    with pytest.raises(TnVenvError) as excinfo:
        create_venv(tmp_path / "x", quiet=True)
    assert "kaboom" in str(excinfo.value)


def test_create_venv_requirements_file_not_found(tmp_path: Path) -> None:
    dest = tmp_path / "venv"
    with pytest.raises(TnVenvError):
        create_venv(dest, requirements=[str(tmp_path / "nope.txt")], quiet=True)


def test_session_result_str_includes_env(tmp_path: Path) -> None:
    r = SessionResult(
        env_dir=tmp_path,
        exe=tmp_path / "bin" / "python",
        bin_path=tmp_path / "bin",
        site_packages=tmp_path / "lib" / "site",
        prompt="myproj",
        python=PythonInfo.from_current(),
    )
    assert str(tmp_path) in str(r)
