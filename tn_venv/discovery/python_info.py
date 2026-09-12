"""Structured description of a Python interpreter."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from functools import total_ordering
from pathlib import Path

from ..errors import DiscoverError
from .query import MARKER, QUERY_SCRIPT

_VERSION_RE = re.compile(
    r"^(?:(?P<impl>cpython|pypy|graalpy|python|py)?[-_]?)?(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.(?P<patch>\d+))?(?:-(?P<arch>32|64))?$",
    re.IGNORECASE,
)

_probe_cache: dict[str, "PythonInfo"] = {}


@total_ordering
@dataclass(frozen=True)
class PythonInfo:
    """Everything tn-venv needs to know about a source interpreter."""

    executable: str
    base_executable: str
    version_info: tuple[int, int, int]
    implementation: str = "cpython"
    prefix: str = ""
    base_prefix: str = ""
    exec_prefix: str = ""
    base_exec_prefix: str = ""
    maxsize: int = sys.maxsize
    machine: str = ""
    stdlib: str = ""
    scripts_nt: str | None = None
    gil_disabled: bool = False
    is_python_build: bool = False
    abiflags: str = ""
    libdir: str | None = None
    ldlibrary: str | None = None
    version: str = ""

    # -- derived -------------------------------------------------------------
    @property
    def version_str(self) -> str:
        return ".".join(str(i) for i in self.version_info)

    @property
    def major_minor(self) -> str:
        return f"{self.version_info[0]}.{self.version_info[1]}"

    @property
    def bits(self) -> int:
        return 64 if self.maxsize > 2**32 else 32

    @property
    def is_64(self) -> bool:
        return self.bits == 64

    @property
    def base_dir(self) -> str:
        """Directory containing the base interpreter binary (pyvenv.cfg home)."""
        return os.path.dirname(self.base_executable or self.executable)

    @property
    def is_freethreaded(self) -> bool:
        return self.gil_disabled

    def __lt__(self, other: "PythonInfo") -> bool:
        return self.version_info < other.version_info

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.implementation}-{self.version_str}-{self.bits}bit @ {self.executable}"

    # -- spec matching ---------------------------------------------------------
    def matches(self, spec: "InterpreterSpec") -> bool:
        if spec.implementation and spec.implementation not in ("python", "py"):
            if spec.implementation != self.implementation:
                return False
            # "python" in a spec means cpython for practical purposes
        if spec.implementation in ("python", "py") and self.implementation != "cpython":
            return False
        if spec.major is not None and self.version_info[0] != spec.major:
            return False
        if spec.minor is not None and self.version_info[1] != spec.minor:
            return False
        if spec.patch is not None and self.version_info[2] != spec.patch:
            return False
        if spec.arch is not None and self.bits != spec.arch:
            return False
        return True

    # -- constructors ------------------------------------------------------------
    @classmethod
    def from_current(cls) -> "PythonInfo":
        """Describe the running interpreter without a subprocess."""
        base_exe = getattr(sys, "_base_executable", None) or sys.executable
        try:
            import sysconfig

            gil = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
            try:
                is_build = bool(sysconfig.is_python_build())
            except Exception:
                is_build = False
            stdlib = sysconfig.get_path("stdlib") or os.path.dirname(os.__file__)
        except Exception:  # pragma: no cover
            gil, is_build, stdlib = False, False, os.path.dirname(os.__file__)
        scripts_nt = None
        if os.name == "nt":
            cand = os.path.join(stdlib, "venv", "scripts", "nt")
            if os.path.isdir(cand):
                scripts_nt = cand
        return cls(
            executable=os.path.abspath(sys.executable),
            base_executable=os.path.abspath(base_exe),
            version_info=tuple(sys.version_info[:3]),
            implementation=getattr(sys.implementation, "name", "cpython"),
            prefix=sys.prefix,
            base_prefix=getattr(sys, "base_prefix", sys.prefix),
            exec_prefix=sys.exec_prefix,
            base_exec_prefix=getattr(sys, "base_exec_prefix", sys.exec_prefix),
            maxsize=sys.maxsize,
            machine=__import__("platform").machine(),
            stdlib=stdlib,
            scripts_nt=scripts_nt,
            gil_disabled=gil,
            is_python_build=is_build,
            version=sys.version.split()[0],
        )

    @classmethod
    def from_exe(
        cls, exe: str | os.PathLike, *, use_cache: bool = True
    ) -> "PythonInfo":
        """Probe the interpreter at *exe* by executing it."""
        exe_str = str(Path(exe).expanduser())
        key = os.path.normcase(os.path.abspath(exe_str))
        if use_cache and key in _probe_cache:
            return _probe_cache[key]
        if not os.path.exists(exe_str):
            raise DiscoverError(f"interpreter does not exist: {exe_str}")
        try:
            proc = subprocess.run(
                [exe_str, "-I", "-c", QUERY_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DiscoverError(
                f"failed to execute interpreter {exe_str!r}: {exc}"
            ) from exc
        out = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
        payload = None
        for line in out.splitlines():
            if line.startswith(MARKER):
                payload = line[len(MARKER) :]
                break
        if proc.returncode != 0 or payload is None:
            err = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
            raise DiscoverError(
                f"{exe_str!r} is not a usable Python interpreter "
                f"(exit {proc.returncode}){': ' + err.strip() if err.strip() else ''}"
            )
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise DiscoverError(
                f"could not parse probe output from {exe_str!r}: {exc}"
            ) from exc
        info = cls(
            executable=os.path.abspath(data["executable"]),
            base_executable=os.path.abspath(
                data.get("base_executable") or data["executable"]
            ),
            version_info=tuple(data["version_info"]),
            implementation=data.get("implementation", "cpython"),
            prefix=data.get("prefix", ""),
            base_prefix=data.get("base_prefix", ""),
            exec_prefix=data.get("exec_prefix", ""),
            base_exec_prefix=data.get("base_exec_prefix", ""),
            maxsize=data.get("maxsize", sys.maxsize),
            machine=data.get("machine", ""),
            stdlib=data.get("stdlib") or "",
            scripts_nt=data.get("scripts_nt"),
            gil_disabled=bool(data.get("gil_disabled")),
            is_python_build=bool(data.get("is_python_build")),
            abiflags=data.get("abiflags", ""),
            libdir=data.get("libdir"),
            ldlibrary=data.get("ldlibrary"),
            version=data.get("version", ""),
        )
        _probe_cache[key] = info
        return info


@dataclass(frozen=True)
class InterpreterSpec:
    """A parsed ``--python`` request: implementation + version + arch."""

    implementation: str | None = None
    major: int | None = None
    minor: int | None = None
    patch: int | None = None
    arch: int | None = None
    raw: str = ""

    @property
    def is_any(self) -> bool:
        return self.major is None

    def describe(self) -> str:
        parts = self.implementation or "python"
        if self.major is not None:
            parts += f"-{self.major}"
            if self.minor is not None:
                parts += f".{self.minor}"
                if self.patch is not None:
                    parts += f".{self.patch}"
        if self.arch:
            parts += f"-{self.arch}bit"
        return parts


def parse_spec(raw: str) -> InterpreterSpec | None:
    """Parse specs like ``3``, ``3.12``, ``3.12.1``, ``python3.12``,
    ``pypy3.10``, ``3.11-64``.  Returns ``None`` when *raw* is not a spec
    (e.g. a filesystem path or bare command name)."""
    m = _VERSION_RE.match(raw.strip())
    if not m:
        return None
    impl = m.group("impl")
    return InterpreterSpec(
        implementation=impl.lower() if impl else None,
        major=int(m.group("major")),
        minor=int(m.group("minor")) if m.group("minor") else None,
        patch=int(m.group("patch")) if m.group("patch") else None,
        arch=int(m.group("arch")) if m.group("arch") else None,
        raw=raw,
    )


def clear_probe_cache() -> None:
    _probe_cache.clear()
