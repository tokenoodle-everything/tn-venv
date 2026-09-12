"""PEP 514 — discover interpreters registered in the Windows registry."""

from __future__ import annotations

import os
from typing import Iterator


def _iter_key(winreg, root, hive_name: str) -> Iterator[tuple[str, str]]:
    """Yield (tag, executable) pairs under a ``Software\\Python`` hive."""
    try:
        with winreg.OpenKey(root, r"Software\Python") as companies:
            i = 0
            while True:
                try:
                    company = winreg.EnumKey(companies, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(companies, company) as tags:
                        j = 0
                        while True:
                            try:
                                tag = winreg.EnumKey(tags, j)
                            except OSError:
                                break
                            j += 1
                            exe = _read_install(winreg, tags, tag)
                            if exe:
                                yield f"{hive_name}/{company}/{tag}", exe
                except OSError:
                    continue
    except OSError:
        return


def _read_install(winreg, tags, tag: str) -> str | None:
    try:
        with winreg.OpenKey(tags, tag + r"\InstallPath") as ip:
            try:
                exe, _ = winreg.QueryValueEx(ip, "ExecutablePath")
                if exe and os.path.exists(exe):
                    return exe
            except OSError:
                pass
            try:
                base, _ = winreg.QueryValueEx(ip, None)  # default value
            except OSError:
                return None
            if base:
                cand = os.path.join(base, "python.exe")
                if os.path.exists(cand):
                    return cand
    except OSError:
        return None
    return None


def registered_pythons() -> Iterator[tuple[str, str]]:
    """Yield ``(source_tag, executable)`` for every PEP 514 registration."""
    if os.name != "nt":
        return
    try:
        import winreg
    except ImportError:  # pragma: no cover
        return
    yield from _iter_key(winreg, winreg.HKEY_CURRENT_USER, "HKCU")
    yield from _iter_key(winreg, winreg.HKEY_LOCAL_MACHINE, "HKLM")
