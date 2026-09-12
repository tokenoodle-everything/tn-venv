"""Pip seeder — installs pip via ensurepip, then optional extras.

Capabilities beyond stdlib ``venv``:

* pin pip to an exact version (``--pip 24.0``) or upgrade to the latest
  release from the index (``--pip latest`` / ``--upgrade-pip``)
* install ``setuptools`` / ``wheel`` (no longer bundled with ensurepip on
  Python ≥ 3.12), optionally pinned
* install arbitrary seed packages (``--with PKG``) and requirement files
  (``--requirements reqs.txt``) right after creation
* offline operation against local wheel directories
  (``--extra-search-dir`` / ``--offline``)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ..create.context import CreatorContext
from ..errors import SeedError
from ..report import Reporter
from ..util.process import clean_pip_env, run_cmd


@dataclass
class SeedResult:
    """What the seeder installed."""

    pip: str | None = None
    setuptools: str | None = None
    wheel: str | None = None
    packages: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    skipped: bool = False


class Seeder:
    """Base seeder interface."""

    name = "none"

    def seed(self, ctx: CreatorContext, report: Reporter) -> SeedResult:
        return SeedResult(skipped=True)


class NoSeeder(Seeder):
    name = "none"


class PipSeeder(Seeder):
    name = "pip"

    def __init__(
        self,
        *,
        pip: str | None = None,
        setuptools: bool | str = False,
        wheel: bool | str = False,
        upgrade_pip: bool = False,
        extra_search_dirs: list[str] | None = None,
        offline: bool = False,
        packages: list[str] | None = None,
        requirements: list[str] | None = None,
    ) -> None:
        #: None → bundled ensurepip version; "latest" → upgrade; else pin
        self.pip = pip
        self.setuptools = setuptools
        self.wheel = wheel
        self.upgrade_pip = upgrade_pip
        self.extra_search_dirs = [
            str(Path(d).expanduser()) for d in (extra_search_dirs or [])
        ]
        self.offline = offline
        self.packages = list(packages or [])
        self.requirements = list(requirements or [])

    # -- helpers ------------------------------------------------------------
    def _env(self) -> dict[str, str]:
        extra: dict[str, str] = {}
        if self.extra_search_dirs:
            extra["PIP_FIND_LINKS"] = os.pathsep.join(self.extra_search_dirs)
        if self.offline:
            extra["PIP_NO_INDEX"] = "1"
        return clean_pip_env(extra)

    def _run_env_python(
        self, ctx: CreatorContext, args: list[str], report: Reporter, what: str
    ):
        exe = str(ctx.env_exe)
        env = self._env()
        env["VIRTUAL_ENV"] = str(ctx.env_dir)
        try:
            return run_cmd([exe, *args], env=env, cwd=ctx.env_dir, report=report)
        except SeedError:
            raise
        except Exception as exc:
            raise SeedError(f"{what} failed: {exc}") from exc

    def _pip_version(self, ctx: CreatorContext, report: Reporter) -> str | None:
        proc = self._run_env_python(
            ctx,
            ["-Im", "pip", "--version"],
            report,
            "pip --version",
        )
        out = proc.stdout.strip() if isinstance(proc.stdout, str) else ""
        # "pip 24.0 from ... (python 3.12)"
        parts = out.split()
        return parts[1] if len(parts) >= 2 and parts[0] == "pip" else None

    # -- main ----------------------------------------------------------------
    def seed(self, ctx: CreatorContext, report: Reporter) -> SeedResult:
        result = SeedResult()

        # 1. bundled pip -------------------------------------------------------
        report.step("installing pip (ensurepip)")
        self._run_env_python(
            ctx,
            ["-Im", "ensurepip", "--upgrade", "--default-pip"],
            report,
            "ensurepip",
        )

        # 2. pin / upgrade pip --------------------------------------------------
        want = "latest" if self.upgrade_pip else self.pip
        if want and want not in ("bundled",):
            spec = "pip --upgrade" if want == "latest" else f"pip=={want}"
            report.step(f"installing {spec}")
            args = ["-Im", "pip", "install", "--quiet"]
            if want == "latest":
                args += ["--upgrade", "pip"]
            else:
                args += [f"pip=={want}"]
            self._run_env_python(ctx, args, report, f"installing {spec}")

        result.pip = self._pip_version(ctx, report)

        # 3. setuptools / wheel ---------------------------------------------------
        to_install: list[str] = []
        if self.setuptools:
            pinned = self.setuptools not in (True, "latest")
            to_install.append(
                f"setuptools=={self.setuptools}" if pinned else "setuptools"
            )
        if self.wheel:
            pinned = self.wheel not in (True, "latest")
            to_install.append(f"wheel=={self.wheel}" if pinned else "wheel")
        if to_install:
            report.step(f"installing {' '.join(to_install)}")
            self._run_env_python(
                ctx,
                ["-Im", "pip", "install", "--quiet", *to_install],
                report,
                f"installing {' '.join(to_install)}",
            )
            result.setuptools = "installed" if self.setuptools else None
            result.wheel = "installed" if self.wheel else None

        # 4. extra seed packages -----------------------------------------------------
        if self.packages:
            report.step(f"installing packages: {', '.join(self.packages)}")
            self._run_env_python(
                ctx,
                ["-Im", "pip", "install", "--quiet", *self.packages],
                report,
                f"installing {', '.join(self.packages)}",
            )
            result.packages = list(self.packages)

        # 5. requirement files ----------------------------------------------------------
        for req in self.requirements:
            req_path = Path(req).expanduser()
            if not req_path.exists():
                raise SeedError(f"requirements file not found: {req}")
            report.step(f"installing requirements from {req_path}")
            self._run_env_python(
                ctx,
                ["-Im", "pip", "install", "--quiet", "-r", str(req_path)],
                report,
                f"installing -r {req_path}",
            )
            result.requirements.append(str(req_path))

        return result


def make_seeder(name: str, **kwargs) -> Seeder:
    """Factory for ``--seeder`` values."""
    if name in ("none", "no", "skip"):
        return NoSeeder()
    if name in ("pip", "ensurepip", "auto"):
        return PipSeeder(**kwargs)
    from ..errors import ConfigError

    raise ConfigError(f"unknown seeder {name!r}; expected one of: pip, none")
