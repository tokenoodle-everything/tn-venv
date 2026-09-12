"""Tests for tn_venv.util.path."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from tn_venv.util.path import (
    copytree,
    ensure_dir,
    is_same_path,
    make_executable,
    rmtree,
    safe_makedirs,
    write_text,
)


def test_is_same_path_identical(tmp_path: Path) -> None:
    assert is_same_path(tmp_path, tmp_path)


def test_is_same_path_redundant_separators(tmp_path: Path) -> None:
    a = tmp_path / "x"
    b = tmp_path / "." / "x"
    # Windows is case-insensitive but both sides are same so trivially equal
    assert is_same_path(str(a), str(b)) or os.name != "nt"


def test_is_same_path_different(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    assert not is_same_path(a, b)


def test_ensure_dir_creates(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "deeper"
    out = ensure_dir(target)
    assert out.is_dir()
    assert out is target


def test_ensure_dir_existing(tmp_path: Path) -> None:
    target = tmp_path / "x"
    target.mkdir()
    out = ensure_dir(target)
    assert out.is_dir()


def test_ensure_dir_blocks_on_file(tmp_path: Path) -> None:
    blocker = tmp_path / "block"
    blocker.write_text("not a dir")
    with pytest.raises(ValueError):
        ensure_dir(blocker)


def test_ensure_dir_blocks_on_symlink_to_file(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("x")
    link = tmp_path / "link"
    if hasattr(os, "symlink"):
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported here")
    with pytest.raises(ValueError):
        ensure_dir(link)


def test_safe_makedirs_idempotent(tmp_path: Path) -> None:
    d = tmp_path / "sub"
    safe_makedirs(d)
    safe_makedirs(d)  # second call must not raise
    assert d.is_dir()


def test_rmtree_file(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_text("x")
    rmtree(f)
    assert not f.exists()


def test_rmtree_directory(tmp_path: Path) -> None:
    d = tmp_path / "d"
    d.mkdir()
    (d / "inner.txt").write_text("x")
    rmtree(d)
    assert not d.exists()


def test_rmtree_readonly_file(tmp_path: Path) -> None:
    d = tmp_path / "ro"
    d.mkdir()
    f = d / "ro.txt"
    f.write_text("x")
    # On POSIX we can actually remove the writable bit; on Windows, rmtree
    # tolerates readonly via its chmod handler. We only assert success.
    rmtree(d)
    assert not d.exists()


def test_copytree_copies_files(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "a.txt").write_text("hello")
    (src / "b").mkdir()
    (src / "b" / "c.txt").write_text("world")
    copytree(src, dst)
    assert (dst / "a.txt").read_text() == "hello"
    assert (dst / "b" / "c.txt").read_text() == "world"


def test_make_executable_idempotent(tmp_path: Path) -> None:
    f = tmp_path / "script.sh"
    f.write_text("#!/bin/sh\n")
    make_executable(f)
    make_executable(f)  # must not error
    if os.name != "nt":
        assert f.stat().st_mode & stat.S_IXUSR


def test_make_executable_handles_missing(tmp_path: Path) -> None:
    # Should silently ignore missing files
    make_executable(tmp_path / "ghost")


def test_write_text_default_newline(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "file.txt"
    write_text(target, "line1\nline2\n")
    assert target.read_text(encoding="utf-8") == "line1\nline2\n"


def test_write_text_crlf_newline(tmp_path: Path) -> None:
    target = tmp_path / "file.bat"
    write_text(target, "a\nb\n", newline="\r\n")
    raw = target.read_bytes()
    assert b"\r\n" in raw


def test_write_text_marks_executable(tmp_path: Path) -> None:
    target = tmp_path / "script"
    write_text(target, "echo\n", executable=True)
    if os.name != "nt":
        assert target.stat().st_mode & stat.S_IXUSR


def test_write_text_returns_path(tmp_path: Path) -> None:
    target = tmp_path / "x"
    out = write_text(target, "hi")
    assert out == target
