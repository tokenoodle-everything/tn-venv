"""Discover interpreters via the Windows ``py`` launcher (PEP 397)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Iterator

_LINE_RE = re.compile(
    r"^\s*-V?:(?P<tag>[\w.\-]+?)\s*\*?\s+(?P<path>.+?python(?:w)?\.exe)\s*$",
    re.IGNORECASE,
)


def py_launcher_pythons() -> Iterator[tuple[str, str]]:
    """Yield ``(tag, executable)`` from ``py -0p`` (available since py 3.11)."""
    if os.name != "nt":
        return
    py = shutil.which("py")
    if not py:
        return
    try:
        proc = subprocess.run(
            [py, "-0p"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return
    if proc.returncode != 0:
        return
    for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            # older format: "-3.12-64  C:\path\python.exe"
            parts = line.split(None, 1)
            if len(parts) == 2 and os.path.exists(parts[1].strip()):
                yield parts[0].lstrip("-"), parts[1].strip()
            continue
        path = m.group("path").strip()
        if os.path.exists(path):
            yield m.group("tag"), path
