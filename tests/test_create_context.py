"""Tests for tn_venv.create.context."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tn_venv.create.context import (
    CreatorContext,
    bin_name_for,
    exe_name_for,
    site_packages_rel,
)
from tn_venv.discovery import PythonInfo


def _ctx(tmp_path: Path, **overrides) -> CreatorContext:
    py = PythonInfo.from_current()
    return CreatorContext(
        env_dir=tmp_path,
        env_name=tmp_path.name,
        prompt="p",
        python=py,
        bin_path=tmp_path / ("Scripts" if sys.platform == "win32" else "bin"),
        lib_path=tmp_path / "lib",
        inc_path=tmp_path / "include",
        cfg_path=tmp_path / "pyvenv.cfg",
        env_exe=(tmp_path / "bin") / "python",
        bin_name="bin",
        **overrides,
    )


def test_bin_name_for_posix() -> None:
    assert bin_name_for("linux") == "bin"
    assert bin_name_for("darwin") == "bin"


def test_bin_name_for_win32() -> None:
    assert bin_name_for("win32") == "Scripts"


def test_bin_name_for_default() -> None:
    # No argument → uses sys.platform
    expected = "Scripts" if sys.platform == "win32" else "bin"
    assert bin_name_for() == expected


def test_site_packages_rel_win32() -> None:
    info = PythonInfo.from_current()
    p = site_packages_rel(info, "win32")
    assert p.parts == ("Lib", "site-packages")


def test_site_packages_rel_posix() -> None:
    info = PythonInfo.from_current()
    p = site_packages_rel(info, "linux")
    assert p == Path("lib") / f"python{info.major_minor}" / "site-packages"


def test_exe_name_for_win32() -> None:
    assert exe_name_for(PythonInfo.from_current(), "win32") == "python.exe"


def test_exe_name_for_posix() -> None:
    assert exe_name_for(PythonInfo.from_current(), "linux") == "python3"


def test_env_var_dir_returns_string_path(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    assert ctx.env_var_dir() == str(tmp_path)


def test_activation_dir_returns_bin_path(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    assert ctx.activation_dir() == ctx.bin_path


def test_purelib_aliases_lib_path(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    assert ctx.purelib == ctx.lib_path


@pytest.mark.skipif(sys.platform != "win32", reason="windows only")
def test_env_exe_w_returns_none_if_missing(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    assert ctx.env_exe_w is None


def test_creator_context_default_flags(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    assert ctx.system_site_packages is False
    assert ctx.symlink is False
    assert ctx.clear is False
    assert ctx.upgrade is False
    assert ctx.command == ""
