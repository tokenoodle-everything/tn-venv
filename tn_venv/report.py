"""Terminal reporting with verbosity levels and optional ANSI colors.

The reporter is intentionally dependency free.  On Windows it enables
Virtual Terminal Processing so modern consoles (Windows Terminal, ConHost
>= TH2, VS Code) render colors; when output is redirected, or ``NO_COLOR``
is set, colors are disabled automatically.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

__all__ = [
    "Reporter",
    "VERBOSITY_QUIET",
    "VERBOSITY_DEFAULT",
    "VERBOSITY_VERBOSE",
    "VERBOSITY_DEBUG",
]

VERBOSITY_QUIET = 0
VERBOSITY_DEFAULT = 1
VERBOSITY_VERBOSE = 2
VERBOSITY_DEBUG = 3

_RESET = "\x1b[0m"
_COLORS = {
    "error": "\x1b[1;31m",  # bold red
    "warn": "\x1b[1;33m",  # bold yellow
    "ok": "\x1b[1;32m",  # bold green
    "info": "\x1b[36m",  # cyan
    "debug": "\x1b[2;37m",  # dim white
    "path": "\x1b[4;36m",  # underlined cyan
    "em": "\x1b[1m",  # bold
}


def _enable_windows_vt() -> bool:
    """Best effort enabling of ANSI processing on legacy conhost."""
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        if mode.value & 0x0004:
            return True
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:  # pragma: no cover - extremely platform specific
        return False


def detect_color(stream=None, force: bool | None = None) -> bool:
    """Decide whether to emit ANSI colors."""
    if force is not None:
        return force and _enable_windows_vt()
    env = os.environ
    if env.get("NO_COLOR"):
        return False
    if env.get("FORCE_COLOR") or env.get("TN_VENV_FORCE_COLOR"):
        return _enable_windows_vt()
    stream = stream or sys.stdout
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if os.name == "nt":
        return _enable_windows_vt()
    return True


@dataclass
class Reporter:
    """Leveled, colored console reporter.

    ``verbosity`` maps to:
      0 → only errors
      1 → errors, warnings, info (default)
      2 → + ok / progress detail
      3 → + debug
    """

    verbosity: int = VERBOSITY_DEFAULT
    color: bool | None = None
    stream: object = None

    def __post_init__(self) -> None:
        if self.stream is None:
            self.stream = sys.stdout
        self._use_color = detect_color(self.stream, self.color)

    # -- formatting helpers ------------------------------------------------
    def style(self, text: str, kind: str) -> str:
        if not self._use_color:
            return text
        return f"{_COLORS.get(kind, '')}{text}{_RESET}"

    def path(self, p: object) -> str:
        return self.style(str(p), "path")

    # -- leveled output ------------------------------------------------------
    def _emit(self, level: int, tag: str, kind: str, message: str) -> None:
        if self.verbosity < level:
            return
        prefix = self.style(tag, kind) if tag else ""
        line = f"{prefix}{message}" if prefix else message
        print(line, file=self.stream)

    def error(self, message: str) -> None:
        self._emit(VERBOSITY_QUIET, "error: ", "error", message)

    def warn(self, message: str) -> None:
        self._emit(VERBOSITY_DEFAULT, "warning: ", "warn", message)

    def info(self, message: str) -> None:
        self._emit(VERBOSITY_DEFAULT, "", "info", message)

    def ok(self, message: str) -> None:
        self._emit(VERBOSITY_VERBOSE, "", "ok", message)

    def step(self, message: str) -> None:
        """A named creation step — shown at default verbosity."""
        self._emit(VERBOSITY_DEFAULT, "==> ", "em", message)

    def debug(self, message: str) -> None:
        self._emit(VERBOSITY_DEBUG, "debug: ", "debug", message)


# A shared null-object reporter for library use when the caller stays silent.
SILENT = Reporter(verbosity=-1)
