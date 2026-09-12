"""Filesystem helpers shared by creators, seeders and activators."""

from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"


def is_same_path(a: os.PathLike | str, b: os.PathLike | str) -> bool:
    """Case-normalising path comparison (Windows-safe)."""
    pa, pb = os.fspath(a), os.fspath(b)
    if IS_WIN:
        return os.path.normcase(os.path.normpath(pa)) == os.path.normcase(
            os.path.normpath(pb)
        )
    return os.path.normpath(pa) == os.path.normpath(pb)


def ensure_dir(path: Path) -> Path:
    """Create *path* (and parents) unless it exists as a directory.

    Mirrors stdlib ``venv`` behaviour: refuse to clobber files/symlinks.
    """
    if path.exists():
        if path.is_symlink() or path.is_file():
            raise ValueError(
                f"unable to create directory {str(path)!r}: blocked by a file"
            )
        return path
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_makedirs(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


def _on_rm_error(func, path, exc_info):  # pragma: no cover - windows only annoyance
    """shutil.rmtree error handler that un-readonly's files (Windows)."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def rmtree(path: Path) -> None:
    """Recursively delete *path*, tolerating read-only files."""
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    if path.exists():
        shutil.rmtree(path, onerror=_on_rm_error)


def copytree(src: Path, dst: Path, *, symlinks: bool = True) -> None:
    shutil.copytree(src, dst, symlinks=symlinks, dirs_exist_ok=True)


def make_executable(path: Path) -> None:
    """chmod +x, no-op on Windows."""
    if IS_WIN:
        return
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass


def write_text(
    path: Path, text: str, *, executable: bool = False, newline: str = "\n"
) -> Path:
    """Write *text* to *path* with controlled newlines."""
    ensure_dir(path.parent)
    path.write_text(text.replace("\n", newline), encoding="utf-8")
    if executable:
        make_executable(path)
    return path
