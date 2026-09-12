"""Candidate interpreter providers.

A *provider* enumerates executables that might satisfy a ``--python``
request.  Providers are tried in order; results are de-duplicated by
resolved executable path.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Iterator, NamedTuple

from .py_launcher import py_launcher_pythons
from .windows_registry import registered_pythons


class Candidate(NamedTuple):
    source: str  # e.g. "PATH", "registry:HKCU/PythonCore/3.12", "py-launcher"
    executable: str


def current_python() -> Iterator[Candidate]:
    yield Candidate("current", sys.executable)


def path_pythons(spec_hint: str | None = None) -> Iterator[Candidate]:
    """Interpreters visible on ``PATH``.

    When *spec_hint* looks like a command name (``python3.12``) only that
    name is probed; otherwise the usual aliases are enumerated.
    """
    names: list[str] = []
    if spec_hint:
        names.append(spec_hint)
    else:
        if os.name == "nt":
            names += ["python.exe", "python3.exe", "pythonw.exe"]
        else:
            names += ["python3", "python", f"python3.{sys.version_info[1]}", "pypy3"]
    seen: set[str] = set()
    for name in names:
        found = shutil.which(name)
        if found and found not in seen:
            seen.add(found)
            yield Candidate("PATH", found)


def registry_pythons() -> Iterator[Candidate]:
    for tag, exe in registered_pythons():
        yield Candidate(f"registry:{tag}", exe)


def launcher_pythons() -> Iterator[Candidate]:
    for tag, exe in py_launcher_pythons():
        yield Candidate(f"py-launcher:{tag}", exe)


def uv_pythons() -> Iterator[Candidate]:
    """Interpreters managed by ``uv`` (``~/.local/share/uv/python`` etc.)."""
    roots: list[Path] = []
    env_dir = os.environ.get("UV_PYTHON_INSTALL_DIR")
    if env_dir:
        roots.append(Path(env_dir))
    if os.name == "nt":
        roaming = os.environ.get("APPDATA")
        if roaming:
            roots.append(Path(roaming) / "uv" / "python")
    else:
        roots.append(Path.home() / ".local" / "share" / "uv" / "python")
    exe_rel = Path("python.exe") if os.name == "nt" else Path("bin") / "python3"
    for root in roots:
        if not root.is_dir():
            continue
        try:
            children = sorted(root.iterdir())
        except OSError:
            continue
        for child in children:
            exe = child / exe_rel
            if exe.exists():
                yield Candidate(f"uv:{child.name}", str(exe))


def pyenv_pythons() -> Iterator[Candidate]:
    """pyenv / pyenv-win shims and versions."""
    root = os.environ.get("PYENV_ROOT")
    candidates: list[Path] = []
    if root:
        candidates.append(Path(root))
    if os.name == "nt":
        candidates.append(Path.home() / ".pyenv" / "pyenv-win" / "versions")
    else:
        candidates.append(Path.home() / ".pyenv" / "versions")
    exe_rel = Path("python.exe") if os.name == "nt" else Path("bin") / "python"
    for base in candidates:
        if not base.is_dir():
            continue
        try:
            children = sorted(base.iterdir())
        except OSError:
            continue
        for child in children:
            exe = child / exe_rel
            if exe.exists():
                yield Candidate(f"pyenv:{child.name}", str(exe))


ALL_PROVIDERS = (
    current_python,
    path_pythons,
    registry_pythons,
    launcher_pythons,
    uv_pythons,
    pyenv_pythons,
)


def iter_candidates(spec_hint: str | None = None) -> Iterator[Candidate]:
    """All discoverable interpreters, de-duplicated by resolved path."""
    seen: set[str] = set()
    for provider in ALL_PROVIDERS:
        try:
            if provider is path_pythons:
                items = provider(spec_hint)
            else:
                items = provider()  # type: ignore[call-arg]
            for cand in items:
                key = os.path.normcase(os.path.realpath(cand.executable))
                if key in seen:
                    continue
                seen.add(key)
                yield cand
        except Exception:
            # a broken provider must never break discovery
            continue
