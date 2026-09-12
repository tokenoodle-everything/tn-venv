"""Typed creation context — the contract between creator, activators, seeder."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from ..discovery import PythonInfo


@dataclass
class CreatorContext:
    """Paths and settings describing the environment being created."""

    env_dir: Path
    env_name: str
    prompt: str
    python: PythonInfo
    bin_path: Path
    lib_path: Path  # site-packages
    inc_path: Path
    cfg_path: Path
    env_exe: Path  # the python executable inside the environment
    bin_name: str  # "Scripts" (Windows) or "bin" (POSIX)
    system_site_packages: bool = False
    symlink: bool = False
    clear: bool = False
    upgrade: bool = False
    command: str = ""  # how the env was created (recorded in pyvenv.cfg)

    @property
    def env_exe_w(self) -> Path | None:
        """The windowed (pythonw) executable, Windows only."""
        if os.name != "nt":
            return None
        cand = self.bin_path / "pythonw.exe"
        return cand if cand.exists() else None

    @property
    def purelib(self) -> Path:
        return self.lib_path

    def activation_dir(self) -> Path:
        return self.bin_path

    def env_var_dir(self) -> str:
        """VIRTUAL_ENV value as written into activation scripts."""
        return str(self.env_dir)


def bin_name_for(platform: str | None = None) -> str:
    platform = platform or sys.platform
    return "Scripts" if platform == "win32" else "bin"


def site_packages_rel(python: PythonInfo, platform: str | None = None) -> Path:
    """site-packages location relative to the env dir."""
    platform = platform or sys.platform
    if platform == "win32":
        return Path("Lib") / "site-packages"
    return Path("lib") / f"python{python.major_minor}" / "site-packages"


def exe_name_for(python: PythonInfo, platform: str | None = None) -> str:
    platform = platform or sys.platform
    if platform == "win32":
        return "python.exe"
    return "python3"
