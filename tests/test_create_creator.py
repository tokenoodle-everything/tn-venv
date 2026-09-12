"""Tests for tn_venv.create.creator — high-level Creator API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tn_venv.create import (
    Creator,
    CreatorContext,
    PosixCreator,
    WindowsCreator,
    make_creator,
)
from tn_venv.create.context import bin_name_for
from tn_venv.errors import CreateError


@pytest.fixture()
def dest(tmp_path: Path) -> Path:
    return tmp_path / "venv"


def _creator(dest: Path, **kwargs) -> Creator:
    from tn_venv.discovery import PythonInfo

    py = PythonInfo.from_current()
    cls = WindowsCreator if sys.platform == "win32" else PosixCreator
    return cls(py, dest, **kwargs)


def test_create_basic_skeleton(dest: Path) -> None:
    creator = _creator(dest)
    ctx = creator.create()
    assert ctx.env_dir == dest
    assert ctx.bin_path.exists()
    assert ctx.lib_path.exists()
    assert ctx.cfg_path.exists()
    assert ctx.env_exe.exists() or ctx.env_exe.is_symlink()


def test_create_writes_pyvenv_cfg(dest: Path) -> None:
    creator = _creator(dest, prompt="myproj")
    creator.create()
    text = (dest / "pyvenv.cfg").read_text(encoding="utf-8")
    assert "home" in text
    assert "implementation" in text
    assert "version_info" in text
    assert "myproj" in text


def test_create_system_site_packages_flag_in_cfg(dest: Path) -> None:
    creator = _creator(dest, system_site_packages=True)
    creator.create()
    text = (dest / "pyvenv.cfg").read_text(encoding="utf-8")
    assert "true" in text.lower()


def test_create_records_command_in_cfg(dest: Path) -> None:
    creator = _creator(dest, command="python -m tn_venv .venv")
    creator.create()
    text = (dest / "pyvenv.cfg").read_text(encoding="utf-8")
    assert "command" in text


def test_create_records_tn_venv_version_in_cfg(dest: Path) -> None:
    creator = _creator(dest)
    creator.create()
    text = (dest / "pyvenv.cfg").read_text(encoding="utf-8")
    assert "tn-venv" in text


def test_create_clear_removes_existing(dest: Path) -> None:
    dest.mkdir()
    (dest / "garbage.txt").write_text("remove me")
    creator = _creator(dest, clear=True)
    creator.create()
    assert not (dest / "garbage.txt").exists()


def test_create_existing_without_clear_raises(dest: Path) -> None:
    dest.mkdir()
    (dest / "pyvenv.cfg").write_text("home = x")
    creator = _creator(dest)
    with pytest.raises(CreateError):
        creator.create()


def test_create_existing_no_cfg_succeeds(dest: Path) -> None:
    # An existing dir without pyvenv.cfg is *not* considered an environment
    dest.mkdir()
    (dest / "file.txt").write_text("kept")
    creator = _creator(dest)
    creator.create()
    assert (dest / "file.txt").exists()


def test_create_with_path_separator_in_dest_raises() -> None:
    # Path containing the separator should be rejected
    from tn_venv.discovery import PythonInfo

    py = PythonInfo.from_current()
    cls = WindowsCreator if sys.platform == "win32" else PosixCreator
    if os.pathsep in "abc":
        pytest.skip("path separator not present in this string")
    bad = Path(f"foo{os.pathsep}bar")
    creator = cls(py, bad)
    with pytest.raises(CreateError):
        creator.create()


def test_create_scm_ignore_none_skips_gitignore(dest: Path) -> None:
    creator = _creator(dest, scm_ignore="none")
    creator.create()
    assert not (dest / ".gitignore").exists()


def test_create_scm_ignore_git_writes_gitignore(dest: Path) -> None:
    creator = _creator(dest, scm_ignore="git")
    creator.create()
    assert (dest / ".gitignore").exists()
    body = (dest / ".gitignore").read_text(encoding="utf-8")
    assert "*" in body


def test_make_creator_picks_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    from tn_venv.discovery import PythonInfo

    py = PythonInfo.from_current()
    c = make_creator(py, Path("/x"), platform="linux")
    assert isinstance(c, PosixCreator)


def test_make_creator_picks_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    from tn_venv.discovery import PythonInfo

    py = PythonInfo.from_current()
    c = make_creator(py, Path("/x"), platform="win32")
    assert isinstance(c, WindowsCreator)


def test_make_creator_default_is_sys_platform() -> None:
    from tn_venv.discovery import PythonInfo

    py = PythonInfo.from_current()
    c = make_creator(py, Path("/x"))
    if sys.platform == "win32":
        assert isinstance(c, WindowsCreator)
    else:
        assert isinstance(c, PosixCreator)


def test_create_context_uses_bin_name_for_platform(dest: Path) -> None:
    creator = _creator(dest)
    ctx = creator.create_context()
    assert ctx.bin_name == bin_name_for()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-specific symlink test")
def test_posix_symlink_creates_symlinks(dest: Path) -> None:
    creator = _creator(dest, symlink=True)
    ctx = creator.create()
    assert ctx.env_exe.is_symlink()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-specific copy test")
def test_posix_copy_creates_regular_files(dest: Path) -> None:
    creator = _creator(dest, symlink=False)
    creator.create()
    assert not dest.joinpath("bin", "python3").is_symlink()
