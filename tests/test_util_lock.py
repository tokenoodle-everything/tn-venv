"""Tests for tn_venv.util.lock.FileLock."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tn_venv.errors import LockError
from tn_venv.util.lock import FileLock


def test_acquire_creates_lock_file(tmp_path: Path) -> None:
    target = tmp_path / "env"
    lock = FileLock(target, timeout=1.0)
    with lock:
        assert lock.lock_path.exists()
    # Released afterwards
    assert not lock.lock_path.exists()


def test_second_acquire_blocks_until_released(tmp_path: Path) -> None:
    # Verify that a contender with a very short timeout raises LockError
    # while another lock is held — proves the contender actually tried to
    # wait on the held lock instead of silently succeeding.
    target = tmp_path / "env"
    a = FileLock(target, timeout=2.0)
    b = FileLock(target, timeout=0.1)
    with a:
        with pytest.raises(LockError):
            with b:
                pass  # pragma: no cover


def test_lock_times_out(tmp_path: Path) -> None:
    target = tmp_path / "env"
    holder = FileLock(target, timeout=1.0)
    contender = FileLock(target, timeout=0.1)
    with holder:
        with pytest.raises(LockError):
            contender.acquire()


def test_stale_lock_is_reclaimed(tmp_path: Path) -> None:
    target = tmp_path / "env"
    # Create a lock file that pretends to belong to a dead process
    lock_path = target.parent / (target.name + ".tn-venv.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("pid=999999 time=0\n", encoding="utf-8")
    lock = FileLock(target, timeout=1.0)
    # Should acquire by reclaiming
    with lock:
        assert lock.lock_path.exists()


def test_acquire_idempotent(tmp_path: Path) -> None:
    # Once released, a fresh acquire must work cleanly.
    target = tmp_path / "env"
    lock = FileLock(target, timeout=1.0)
    with lock:
        assert lock.lock_path.exists()
    # After release, acquire should succeed again
    with lock:
        assert lock.lock_path.exists()


def test_release_removes_lock_file(tmp_path: Path) -> None:
    target = tmp_path / "env"
    lock = FileLock(target, timeout=1.0)
    lock.acquire()
    assert lock.lock_path.exists()
    lock.release()
    assert not lock.lock_path.exists()


def test_release_without_acquire_is_safe(tmp_path: Path) -> None:
    target = tmp_path / "env"
    lock = FileLock(target)
    lock.release()  # no-op, must not raise


def test_lock_payload_contains_pid(tmp_path: Path) -> None:
    target = tmp_path / "env"
    lock = FileLock(target, timeout=1.0)
    with lock:
        text = lock.lock_path.read_text(encoding="utf-8")
    assert f"pid={os.getpid()}" in text


def test_lock_with_missing_parent_dir(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "env"
    lock = FileLock(target, timeout=1.0)
    # Should create the parent directory and succeed
    with lock:
        assert lock.lock_path.exists()


def test_lock_creates_parent_dir_on_retry(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "env"
    # Pre-create a stale lock file in a sibling
    lock_path = target.parent / (target.name + ".tn-venv.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # Don't write any stale content — just exercise acquire on fresh dir
    lock = FileLock(target, timeout=0.5)
    with lock:
        assert lock.lock_path.exists()
