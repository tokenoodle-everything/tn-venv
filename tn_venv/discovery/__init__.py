"""Interpreter discovery: turn a ``--python`` request into a PythonInfo.

Resolution order for a spec:

1. no spec           → the interpreter running tn-venv
2. existing path     → probe it directly
3. command on PATH   → probe the resolved executable
4. version-ish spec  → scan all providers, pick the highest matching version
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..errors import DiscoverError, InterpreterNotFoundError
from ..report import Reporter, SILENT
from .providers import Candidate, iter_candidates
from .python_info import InterpreterSpec, PythonInfo, clear_probe_cache, parse_spec

__all__ = [
    "PythonInfo",
    "InterpreterSpec",
    "discover",
    "discover_all",
    "parse_spec",
    "clear_probe_cache",
]


def _looks_like_path(spec: str) -> bool:
    if os.path.exists(os.path.expanduser(spec)):
        return True
    sep_hit = (os.sep in spec) or (os.altsep is not None and os.altsep in spec)
    return sep_hit or spec.lower().endswith(".exe") or spec.startswith(".")


def discover(
    specs: str | list[str] | None = None,
    *,
    report: Reporter = SILENT,
) -> PythonInfo:
    """Resolve the first satisfiable spec into a probed :class:`PythonInfo`."""
    if specs is None:
        specs = []
    if isinstance(specs, str):
        specs = [specs]
    if not specs:
        report.debug("no --python given; using the running interpreter")
        return PythonInfo.from_current()

    errors: list[str] = []
    for raw in specs:
        raw = raw.strip()
        if not raw:
            continue
        try:
            return _discover_one(raw, report=report)
        except InterpreterNotFoundError as exc:
            errors.append(str(exc))
            report.debug(f"spec {raw!r} not satisfiable: {exc.spec}")
        except DiscoverError as exc:
            errors.append(str(exc))
            report.debug(f"spec {raw!r} failed: {exc}")
    raise InterpreterNotFoundError(", ".join(specs), tried=errors)


def _discover_one(raw: str, *, report: Reporter) -> PythonInfo:
    # 1. explicit path ------------------------------------------------------
    if _looks_like_path(raw):
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        report.debug(f"probing interpreter path {path}")
        return PythonInfo.from_exe(path)

    # 2. command name on PATH ------------------------------------------------
    spec = parse_spec(raw)
    if spec is None or _is_commandish(raw):
        resolved = shutil.which(raw)
        if resolved:
            info = PythonInfo.from_exe(resolved)
            if spec is None or info.matches(spec):
                report.debug(f"resolved {raw!r} via PATH → {resolved}")
                return info

    if spec is None:
        raise InterpreterNotFoundError(raw)

    # 3. version-ish spec: scan providers --------------------------------------
    return _match_spec(spec, report=report)


def _is_commandish(raw: str) -> bool:
    """``python3.12`` should first try PATH as a command named literally."""
    lowered = raw.lower()
    if os.name == "nt" and not lowered.endswith(".exe"):
        return False
    return lowered.startswith(("python", "pypy")) and os.sep not in raw


def _match_spec(spec: InterpreterSpec, *, report: Reporter) -> PythonInfo:
    hint = spec.raw if _is_commandish(spec.raw) else None
    matches: list[tuple[PythonInfo, Candidate]] = []
    tried: list[str] = []
    for cand in iter_candidates(hint):
        try:
            info = PythonInfo.from_exe(cand.executable)
        except DiscoverError as exc:
            tried.append(f"{cand.executable} ({exc})")
            continue
        if info.matches(spec):
            matches.append((info, cand))
    if not matches:
        raise InterpreterNotFoundError(spec.raw or spec.describe(), tried=tried)
    # prefer exact patch matches, then the newest version, current-python first
    matches.sort(
        key=lambda m: (m[0].version_info, m[1].source == "current"), reverse=True
    )
    info, cand = matches[0]
    report.debug(f"spec {spec.raw!r} matched {info.executable} via {cand.source}")
    return info


def discover_all(*, report: Reporter = SILENT) -> list[tuple[PythonInfo, str]]:
    """Probe every discoverable interpreter (for ``--list-pythons``)."""
    found: list[tuple[PythonInfo, str]] = []
    for cand in iter_candidates():
        try:
            info = PythonInfo.from_exe(cand.executable)
        except DiscoverError:
            continue
        found.append((info, cand.source))
    found.sort(key=lambda t: t[0].version_info, reverse=True)
    return found
