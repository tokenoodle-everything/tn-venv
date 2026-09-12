"""A small, dependency-free inter-process file lock.

Used to serialise concurrent creation of the same environment directory
(two terminals running ``tn-venv .venv`` at once).  The lock is a file
created with ``O_CREAT | O_EXCL``; stale locks (holder process dead) are
reclaimed automatically.
"""

from __future__ import annotations

import os
import socket
import time
from pathlib import Path

from ..errors import LockError

_DEFAULT_TIMEOUT = 120.0
_POLL_INTERVAL = 0.05
_STALE_AFTER = 600.0  # seconds; a lock older than this with a dead pid is stale


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            handle = kernel32.OpenProcess(
                0x1000, False, pid
            )  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return code.value == 259  # STILL_ACTIVE
                return False
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return True  # assume alive when we cannot tell
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class FileLock:
    """Context-manager lock guarding an environment directory."""

    def __init__(self, target: Path, *, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self.lock_path = target.parent / (target.name + ".tn-venv.lock")
        self.timeout = timeout
        self._fd: int | None = None

    # -- helpers ------------------------------------------------------------
    def _payload(self) -> bytes:
        return f"pid={os.getpid()} host={socket.gethostname()} time={time.time()}\n".encode()

    def _is_stale(self) -> bool:
        try:
            text = self.lock_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        pid = -1
        for part in text.split():
            if part.startswith("pid="):
                try:
                    pid = int(part[4:])
                except ValueError:
                    pid = -1
        if pid > 0 and _pid_alive(pid):
            return False
        try:
            age = time.time() - self.lock_path.stat().st_mtime
        except OSError:
            return False
        return age > _STALE_AFTER or (pid > 0 and not _pid_alive(pid))

    def _try_acquire(self) -> bool:
        try:
            self._fd = os.open(
                str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY
            )
        except FileExistsError:
            return False
        except OSError:
            # directory does not exist yet / permissions — create parent then retry once
            try:
                self.lock_path.parent.mkdir(parents=True, exist_ok=True)
                self._fd = os.open(
                    str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
            except OSError:
                return False
        os.write(self._fd, self._payload())
        return True

    # -- context manager protocol -------------------------------------------
    def acquire(self) -> "FileLock":
        deadline = time.monotonic() + self.timeout
        while True:
            if self._try_acquire():
                return self
            if self._is_stale():
                try:
                    self.lock_path.unlink(missing_ok=True)
                except OSError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise LockError(
                    f"timed out after {self.timeout:.0f}s waiting for lock {str(self.lock_path)!r}; "
                    "another tn-venv process may be creating this environment"
                )
            time.sleep(_POLL_INTERVAL)

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None
        try:
            self.lock_path.unlink(missing_ok=True)
        except OSError:
            pass

    def __enter__(self) -> "FileLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
