"""Session orchestration: resolve options, run the creation pipeline.

The pipeline is::

    discover interpreter → lock directory → create skeleton + python
    → generate activators → seed pip/packages → report summary

Both the CLI (:func:`tn_venv.cli.cli_run`) and the Python API
(:func:`tn_venv.create_venv`) funnel into :func:`run_session`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .config.spec import OPTION_SPECS
from .create import CreatorContext, make_creator
from .create.activators import resolve_activators
from .discovery import PythonInfo, discover
from .errors import ConfigError, TNError
from .report import Reporter, SILENT
from .seed import SeedResult, make_seeder
from .util.lock import FileLock

HARD_DEFAULTS: dict[str, object] = {
    spec.dest: spec.default for spec in OPTION_SPECS.values()
}


@dataclass
class Options:
    """Fully resolved creation options."""

    dest: Path = Path(".venv")
    python: list[str] = field(default_factory=list)
    clear: bool = False
    upgrade: bool = False
    system_site_packages: bool = False
    symlinks: bool | None = None
    copies: bool | None = None
    scm_ignore: str = "git"
    seeder: str = "pip"
    no_pip: bool = False
    pip: str | None = None
    upgrade_pip: bool = False
    setuptools: str | None = None
    wheel: str | None = None
    extra_search_dir: list[str] = field(default_factory=list)
    offline: bool = False
    seed_packages: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    activators: list[str] = field(default_factory=list)
    prompt: str | None = None
    quiet: int = 0
    verbose: int = 0
    color: bool | None = None
    command: str = ""

    # -- derived -------------------------------------------------------------
    @property
    def use_symlinks(self) -> bool:
        if self.symlinks and self.copies:
            raise ConfigError("cannot pass both --symlinks and --copies")
        if self.symlinks is not None:
            return bool(self.symlinks)
        if self.copies is not None:
            return not self.copies
        return os.name != "nt"  # copies on Windows, symlinks elsewhere

    @property
    def verbosity(self) -> int:
        level = 1 + (self.verbose or 0) - (self.quiet or 0)
        return max(0, min(3, level))

    @property
    def wants_pip(self) -> bool:
        return not self.no_pip and self.seeder != "none"

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "Options":
        known = {f for f in cls.__dataclass_fields__ if f != "command"}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in values.items() if k in known and v is not None}
        # normalise list-typed fields
        for key in (
            "python",
            "extra_search_dir",
            "seed_packages",
            "requirements",
            "activators",
        ):
            if key in filtered and filtered[key] is None:
                filtered[key] = []
        return cls(**filtered)  # type: ignore[arg-type]


@dataclass
class SessionResult:
    """Returned by :func:`run_session` / :func:`create_venv`."""

    env_dir: Path
    exe: Path
    bin_path: Path
    site_packages: Path
    prompt: str
    python: PythonInfo
    activation_scripts: list[Path] = field(default_factory=list)
    seed: SeedResult | None = None

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"<venv {self.env_dir} python={self.python.version_str}>"


def merge_config(
    cli_values: dict[str, object],
    env_values: dict[str, object] | None = None,
    file_values: dict[str, object] | None = None,
) -> dict[str, object]:
    """Merge resolved config layers into final values."""
    merged: dict[str, object] = dict(HARD_DEFAULTS)
    for layer in (file_values or {}, env_values or {}, cli_values):
        for key, value in layer.items():
            if value is None:
                continue
            merged[key] = value
    return merged


def run_session(options: Options, reporter: Reporter | None = None) -> SessionResult:
    """Execute the full creation pipeline described by *options*."""
    reporter = reporter or Reporter(verbosity=options.verbosity, color=options.color)

    dest = options.dest.expanduser()
    if not dest.is_absolute():
        dest = Path.cwd() / dest
    dest = dest.resolve() if not dest.exists() else dest
    if not dest.is_absolute():
        dest = Path(os.path.abspath(dest))

    reporter.step(f"creating virtual environment at {reporter.path(dest)}")

    # -- 1. discover -------------------------------------------------------
    specs = list(options.python)
    python = discover(specs if specs else None, report=reporter)
    reporter.info(
        f"interpreter: {reporter.style(python.implementation, 'em')} "
        f"{python.version_str} ({python.bits}-bit) from {reporter.path(python.base_executable)}"
    )

    # -- 2. create under lock -------------------------------------------------
    with FileLock(dest):
        creator = make_creator(
            python,
            dest,
            prompt=options.prompt,
            system_site_packages=options.system_site_packages,
            symlink=options.use_symlinks,
            clear=options.clear,
            upgrade=options.upgrade,
            scm_ignore=options.scm_ignore,
            command=options.command,
            report=reporter,
        )
        ctx: CreatorContext = creator.create()
        reporter.ok(f"python binaries installed to {ctx.bin_path}")

        # -- 3. activators -----------------------------------------------------
        scripts: list[Path] = []
        for activator in resolve_activators(options.activators or None):
            written = activator.generate(ctx)
            scripts.extend(written)
        if scripts:
            reporter.ok(f"{len(scripts)} activation script(s) generated")

        # -- 4. seed -------------------------------------------------------------
        seed_result: SeedResult | None = None
        if options.wants_pip:
            seeder = make_seeder(
                "pip",
                pip=options.pip,
                setuptools=options.setuptools,
                wheel=options.wheel,
                upgrade_pip=options.upgrade_pip,
                extra_search_dirs=options.extra_search_dir,
                offline=options.offline,
                packages=options.seed_packages,
                requirements=options.requirements,
            )
            seed_result = seeder.seed(ctx, reporter)
            if seed_result.pip:
                reporter.ok(f"pip {seed_result.pip} installed")
        else:
            reporter.debug("seeder disabled; skipping pip installation")

    result = SessionResult(
        env_dir=ctx.env_dir,
        exe=ctx.env_exe,
        bin_path=ctx.bin_path,
        site_packages=ctx.lib_path,
        prompt=ctx.prompt,
        python=python,
        activation_scripts=scripts,
        seed=seed_result,
    )
    reporter.step(f"environment ready: {reporter.path(ctx.env_exe)}")
    _print_activation_hint(ctx, reporter)
    return result


def _print_activation_hint(ctx: CreatorContext, reporter: Reporter) -> None:
    if os.name == "nt":
        hint = f"{ctx.bin_path}\\Activate.ps1  (PowerShell)  |  {ctx.bin_path}\\activate.bat  (cmd)"
    else:
        hint = f"source {ctx.bin_path}/activate"
    reporter.info(f"activate with: {reporter.style(hint, 'em')}")


def create_venv(
    dest: str | os.PathLike = ".venv",
    *,
    python: str | list[str] | None = None,
    clear: bool = False,
    upgrade: bool = False,
    system_site_packages: bool = False,
    symlinks: bool | None = None,
    copies: bool | None = None,
    with_pip: bool = True,
    pip: str | None = None,
    setuptools: bool | str = False,
    wheel: bool | str = False,
    upgrade_pip: bool = False,
    packages: list[str] | None = None,
    requirements: list[str] | None = None,
    activators: list[str] | None = None,
    prompt: str | None = None,
    offline: bool = False,
    extra_search_dir: list[str] | None = None,
    quiet: bool = True,
) -> SessionResult:
    """Programmatic API — create a virtual environment in one call.

    >>> from tn_venv import create_venv
    >>> result = create_venv(".venv", packages=["requests"])  # doctest: +SKIP
    >>> result.exe  # the environment's python            # doctest: +SKIP
    """
    python_specs: list[str]
    if python is None:
        python_specs = []
    elif isinstance(python, str):
        python_specs = [python]
    else:
        python_specs = list(python)
    options = Options(
        dest=Path(dest),
        python=python_specs,
        clear=clear,
        upgrade=upgrade,
        system_site_packages=system_site_packages,
        symlinks=symlinks,
        copies=copies,
        seeder="pip" if with_pip else "none",
        no_pip=not with_pip,
        pip=pip,
        setuptools="latest" if setuptools is True else (setuptools or None),
        wheel="latest" if wheel is True else (wheel or None),
        upgrade_pip=upgrade_pip,
        seed_packages=list(packages or []),
        requirements=list(requirements or []),
        activators=list(activators or []),
        prompt=prompt,
        offline=offline,
        extra_search_dir=list(extra_search_dir or []),
    )
    reporter = SILENT if quiet else Reporter(verbosity=1)
    try:
        return run_session(options, reporter)
    except TNError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise TNError(f"unexpected failure while creating {dest}: {exc}") from exc
