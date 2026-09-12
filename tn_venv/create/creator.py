"""The environment creator — lays down the on-disk virtual environment.

Two concrete creators exist, selected by the *host* platform:

* :class:`WindowsCreator` — copies the ``venvlauncher`` redirector binaries
  (Python ≥ 3.11) or the real ``python.exe`` plus its DLLs (older), or
  symlinks everything when requested and permitted.
* :class:`PosixCreator` — symlinks (default) or copies the interpreter
  binary and creates the ``lib/pythonX.Y/site-packages`` layout.

The logic deliberately mirrors CPython's own :mod:`venv` so the produced
environments are indistinguishable from ``python -m venv`` output.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ..discovery import PythonInfo
from ..errors import CreateError
from ..report import Reporter, SILENT
from ..util.path import ensure_dir, is_same_path, make_executable, rmtree
from .context import CreatorContext, bin_name_for, exe_name_for, site_packages_rel


class Creator:
    """Base class: directory skeleton, pyvenv.cfg, scm-ignore files."""

    def __init__(
        self,
        python: PythonInfo,
        dest: Path,
        *,
        prompt: str | None = None,
        system_site_packages: bool = False,
        symlink: bool = False,
        clear: bool = False,
        upgrade: bool = False,
        scm_ignore: str = "git",
        command: str = "",
        report: Reporter = SILENT,
    ) -> None:
        self.python = python
        self.dest = dest
        self.prompt = prompt
        self.system_site_packages = system_site_packages
        self.symlink = symlink
        self.clear = clear
        self.upgrade = upgrade
        self.scm_ignore = scm_ignore
        self.command = command
        self.report = report

    # -- public API ---------------------------------------------------------
    def create(self) -> CreatorContext:
        if os.pathsep in str(self.dest):
            raise CreateError(
                f"refusing to create a virtual environment in {str(self.dest)!r} "
                f"because it contains the PATH separator {os.pathsep!r}"
            )
        if self.clear and self.dest.exists():
            self.report.debug(f"clearing existing directory {self.dest}")
            rmtree(self.dest)
        self._check_not_nested()
        ctx = self.create_context()
        self.ensure_directories(ctx)
        self.setup_python(ctx)
        self.create_configuration(ctx)
        self.create_scm_ignore(ctx)
        return ctx

    # -- guards ---------------------------------------------------------------
    def _check_not_nested(self) -> None:
        if self.dest.exists() and not self.clear and not self.upgrade:
            cfg = self.dest / "pyvenv.cfg"
            if cfg.exists():
                raise CreateError(
                    f"{str(self.dest)!r} already contains a virtual environment; "
                    "use --clear to replace it or --upgrade to refresh it in place"
                )

    # -- skeleton -----------------------------------------------------------
    def create_context(self) -> CreatorContext:
        env_dir = self.dest
        env_name = env_dir.name
        bin_name = bin_name_for()
        bin_path = env_dir / bin_name
        lib_path = env_dir / site_packages_rel(self.python)
        inc_path = env_dir / ("Include" if os.name == "nt" else "include")
        exe_name = exe_name_for(self.python)
        return CreatorContext(
            env_dir=env_dir,
            env_name=env_name,
            prompt=self.prompt if self.prompt is not None else env_name,
            python=self.python,
            bin_path=bin_path,
            lib_path=lib_path,
            inc_path=inc_path,
            cfg_path=env_dir / "pyvenv.cfg",
            env_exe=bin_path / exe_name,
            bin_name=bin_name,
            system_site_packages=self.system_site_packages,
            symlink=self.symlink,
            clear=self.clear,
            upgrade=self.upgrade,
            command=self.command,
        )

    def ensure_directories(self, ctx: CreatorContext) -> None:
        for path in (ctx.env_dir, ctx.inc_path, ctx.lib_path, ctx.bin_path):
            try:
                ensure_dir(path)
            except ValueError as exc:
                raise CreateError(str(exc)) from exc
        # issue 21197: lib64 → lib on 64-bit POSIX (except macOS)
        if os.name == "posix" and sys.platform != "darwin" and self.python.is_64:
            link = ctx.env_dir / "lib64"
            if not link.exists():
                try:
                    os.symlink("lib", str(link))
                except OSError as exc:  # pragma: no cover
                    self.report.warn(f"could not create lib64 symlink: {exc}")

    # -- pyvenv.cfg ------------------------------------------------------------
    def create_configuration(self, ctx: CreatorContext) -> None:
        lines = [
            f"home = {self.python.base_dir}",
            f"implementation = {self.python.implementation}",
            f"version_info = {self.python.version_str}",
            f"include-system-site-packages = {'true' if self.system_site_packages else 'false'}",
            f"version = {self.python.version_str}",
        ]
        if self.prompt is not None:
            lines.append(f"prompt = {self.prompt!r}")
        base_exe = os.path.realpath(self.python.base_executable)
        lines.append(f"executable = {base_exe}")
        lines.append(f"base-executable = {base_exe}")
        if self.command:
            lines.append(f"command = {self.command}")
        from ..version import __version__

        lines.append(f"tn-venv = {__version__}")
        content = "\n".join(lines) + "\n"
        ctx.cfg_path.write_text(content, encoding="utf-8")
        self.report.debug(f"wrote {ctx.cfg_path}:\n{content.rstrip()}")

    def create_scm_ignore(self, ctx: CreatorContext) -> None:
        if self.scm_ignore == "none":
            return
        if self.scm_ignore == "git":
            target = ctx.env_dir / ".gitignore"
            target.write_text(
                "# created by tn-venv — ignore everything in this directory\n*\n",
                encoding="utf-8",
            )

    # -- to be implemented per platform ---------------------------------------
    def setup_python(self, ctx: CreatorContext) -> None:  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------
class WindowsCreator(Creator):
    """Windows creator.

    Copy mode (default): installs ``venvlauncher.exe`` / ``venvwlauncher.exe``
    from the source interpreter's stdlib (Python ≥ 3.11).  When launchers are
    unavailable (older Pythons, source builds) it falls back to copying the
    real executables plus their runtime DLLs — the pre-3.11 stdlib behaviour,
    hardened the way virtualenv does it.

    Symlink mode: symlinks the real executables and every ``python*`` /
    ``vcruntime*`` DLL; on ``OSError`` (no privilege) falls back to copies.
    """

    def setup_python(self, ctx: CreatorContext) -> None:
        py = self.python
        bin_path = ctx.bin_path
        dirname = py.base_dir
        debug = os.path.basename(py.base_executable).lower().endswith("_d.exe")
        suffix = "_d" if debug else ""

        link_sources, copy_sources = self._source_maps(dirname, suffix, py)

        do_copies = True
        if self.symlink:
            do_copies = False
            # symlinking needs the runtime DLLs alongside the executables
            try:
                for fname in os.listdir(dirname):
                    low = fname.lower()
                    if low.startswith(("python", "vcruntime")) and low.endswith(".dll"):
                        link_sources[fname] = os.path.join(dirname, fname)
            except OSError:
                pass
            made: list[Path] = []
            for dest_name, src in link_sources.items():
                dest = bin_path / dest_name
                try:
                    if dest.exists() or dest.is_symlink():
                        dest.unlink()
                    os.symlink(src, str(dest))
                    made.append(dest)
                except OSError as exc:
                    self.report.warn(
                        f"unable to symlink {src} → {dest}: {exc}; falling back to copies"
                    )
                    do_copies = True
                    for f in made:
                        try:
                            f.unlink()
                        except OSError:
                            pass
                    break

        if do_copies:
            for dest_name, src in copy_sources.items():
                dest = bin_path / dest_name
                try:
                    shutil.copy2(src, str(dest))
                    self.report.debug(f"copied {src} → {dest}")
                except OSError as exc:
                    if dest_name in ("python.exe", f"python{suffix}.exe"):
                        raise CreateError(
                            f"cannot install interpreter binary: {exc}"
                        ) from exc
                    self.report.warn(f"unable to copy {src} → {dest}: {exc}")
            if self._used_real_exe(copy_sources):
                self._copy_runtime_dlls(dirname, bin_path)

        if py.is_python_build:
            self._copy_tcl(dirname, ctx)

    # -- helpers ---------------------------------------------------------------
    def _source_maps(self, dirname: str, suffix: str, py: PythonInfo):
        """Return (link_sources, copy_sources) name→path maps."""
        gil_enabled = not py.gil_disabled
        if py.is_python_build:
            scripts = dirname
        else:
            scripts = py.scripts_nt or ""
        if gil_enabled:
            real_exe = os.path.join(dirname, f"python{suffix}.exe")
            real_w = os.path.join(dirname, f"pythonw{suffix}.exe")
            link_sources = {
                "python.exe": real_exe,
                f"python{suffix}.exe": real_exe,
                "pythonw.exe": real_w,
                f"pythonw{suffix}.exe": real_w,
            }
            launcher = os.path.join(scripts, f"venvlauncher{suffix}.exe")
            wlauncher = os.path.join(scripts, f"venvwlauncher{suffix}.exe")
            if os.path.exists(launcher):
                copy_sources = {
                    "python.exe": launcher,
                    f"python{suffix}.exe": launcher,
                }
                if os.path.exists(wlauncher):
                    copy_sources["pythonw.exe"] = wlauncher
                    copy_sources[f"pythonw{suffix}.exe"] = wlauncher
            else:
                # < 3.11: copy the real binaries
                copy_sources = {"python.exe": real_exe, f"python{suffix}.exe": real_exe}
                if os.path.exists(real_w):
                    copy_sources["pythonw.exe"] = real_w
                    copy_sources[f"pythonw{suffix}.exe"] = real_w
        else:  # free-threaded build
            t = f"3.{py.version_info[1]}t"
            real_exe = os.path.join(dirname, f"python{t}{suffix}.exe")
            real_w = os.path.join(dirname, f"pythonw{t}{suffix}.exe")
            if not os.path.exists(real_exe):
                real_exe = os.path.join(dirname, f"python{suffix}.exe")
                real_w = os.path.join(dirname, f"pythonw{suffix}.exe")
            link_sources = {
                "python.exe": real_exe,
                f"python{suffix}.exe": real_exe,
                f"python{t}.exe": real_exe,
                f"python{t}{suffix}.exe": real_exe,
                "pythonw.exe": real_w,
                f"pythonw{suffix}.exe": real_w,
            }
            launcher = os.path.join(scripts, f"venvlaunchert{suffix}.exe")
            wlauncher = os.path.join(scripts, f"venvwlaunchert{suffix}.exe")
            if os.path.exists(launcher):
                copy_sources = {
                    "python.exe": launcher,
                    f"python{suffix}.exe": launcher,
                    f"python{t}.exe": launcher,
                    f"python{t}{suffix}.exe": launcher,
                    "pythonw.exe": wlauncher,
                    f"pythonw{suffix}.exe": wlauncher,
                }
            else:
                copy_sources = link_sources
        # drop entries whose source does not exist
        link_sources = {k: v for k, v in link_sources.items() if os.path.exists(v)}
        copy_sources = {k: v for k, v in copy_sources.items() if os.path.exists(v)}
        return link_sources, copy_sources

    def _used_real_exe(self, copy_sources: dict[str, str]) -> bool:
        src = copy_sources.get("python.exe", "")
        return os.path.basename(src).lower().startswith("python")

    def _copy_runtime_dlls(self, dirname: str, bin_path: Path) -> None:
        """Copy python*.dll / vcruntime*.dll next to a copied real exe."""
        try:
            names = os.listdir(dirname)
        except OSError:
            return
        for fname in names:
            low = fname.lower()
            if low.startswith(("python", "vcruntime")) and low.endswith(".dll"):
                src = os.path.join(dirname, fname)
                dest = bin_path / fname
                if not dest.exists():
                    try:
                        shutil.copy2(src, str(dest))
                    except OSError as exc:
                        self.report.warn(f"unable to copy runtime DLL {fname}: {exc}")

    def _copy_tcl(self, dirname: str, ctx: CreatorContext) -> None:  # pragma: no cover
        for root, _dirs, files in os.walk(dirname):
            if "init.tcl" in files:
                tcl_name = os.path.basename(root)
                tcl_dest = ctx.env_dir / "Lib" / tcl_name
                tcl_dest.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(
                    os.path.join(root, "init.tcl"), str(tcl_dest / "init.tcl")
                )
                break


# ---------------------------------------------------------------------------
# POSIX
# ---------------------------------------------------------------------------
class PosixCreator(Creator):
    """POSIX creator: symlinks by default, copies on request/failure."""

    def setup_python(self, ctx: CreatorContext) -> None:
        bin_path = ctx.bin_path
        src_exe = self.python.base_executable
        if not os.path.exists(src_exe):
            src_exe = self.python.executable
        env_exe = ctx.env_exe

        self._link_or_copy(src_exe, env_exe)
        if not env_exe.is_symlink():
            make_executable(env_exe)

        suffixes = ["python", "python3", f"python3.{self.python.version_info[1]}"]
        if self.python.implementation == "pypy":
            suffixes.insert(0, "pypy3")
        for name in suffixes:
            path = bin_path / name
            if path == env_exe or path.exists() or path.is_symlink():
                continue
            self._link_or_copy(env_exe, path, relative_ok=True)
            if not path.is_symlink():
                make_executable(path)

    def _link_or_copy(self, src, dst: Path, *, relative_ok: bool = False) -> None:
        force_copy = not self.symlink
        if dst.exists() or dst.is_symlink():
            if is_same_path(os.path.realpath(dst), os.path.realpath(src)):
                return
            try:
                dst.unlink()
            except OSError:
                pass
        if not force_copy:
            try:
                if relative_ok and Path(src).parent == dst.parent:
                    os.symlink(os.path.basename(os.fspath(src)), str(dst))
                else:
                    os.symlink(os.fspath(src), str(dst))
                return
            except OSError as exc:
                self.report.warn(
                    f"unable to symlink {src} → {dst}: {exc}; copying instead"
                )
                force_copy = True
        if force_copy:
            try:
                shutil.copyfile(os.fspath(src), str(dst))
            except OSError as exc:
                raise CreateError(
                    f"cannot install interpreter binary {src}: {exc}"
                ) from exc


def make_creator(
    python: PythonInfo,
    dest: Path,
    *,
    platform: str | None = None,
    **kwargs,
) -> Creator:
    """Factory: pick the creator matching the host platform."""
    platform = platform or sys.platform
    cls: type[Creator]
    if platform == "win32":
        cls = WindowsCreator
    else:
        cls = PosixCreator
    return cls(python, dest, **kwargs)
