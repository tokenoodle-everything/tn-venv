"""Tests for tn_venv.create.activators."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from tn_venv.create.activators import (
    DEFAULT_ACTIVATORS,
    BashActivator,
    BatchActivator,
    CShActivator,
    FishActivator,
    NushellActivator,
    PowerShellActivator,
    PythonActivator,
    available_activators,
    resolve_activators,
)
from tn_venv.create.activators.base import Activator
from tn_venv.create.context import CreatorContext
from tn_venv.discovery import PythonInfo
from tn_venv.errors import ActivateError, ConfigError


def _ctx(tmp_path: Path, **overrides) -> CreatorContext:
    py = PythonInfo.from_current()
    bin_name = "Scripts" if sys.platform == "win32" else "bin"
    return CreatorContext(
        env_dir=tmp_path,
        env_name=tmp_path.name,
        prompt="myproj",
        python=py,
        bin_path=tmp_path / bin_name,
        lib_path=tmp_path / "lib" / "site-packages",
        inc_path=tmp_path / "include",
        cfg_path=tmp_path / "pyvenv.cfg",
        env_exe=tmp_path
        / bin_name
        / ("python.exe" if sys.platform == "win32" else "python3"),
        bin_name=bin_name,
        **overrides,
    )


def test_available_activators_contains_known() -> None:
    names = available_activators()
    assert "bash" in names
    assert "powershell" in names
    assert "fish" in names


def test_default_activators_matches_registry() -> None:
    assert set(DEFAULT_ACTIVATORS) == set(available_activators())


def test_resolve_activators_default_is_all() -> None:
    items = resolve_activators(None)
    assert {a.name for a in items} == set(available_activators())


def test_resolve_activators_explicit_default() -> None:
    items = resolve_activators(["default"])
    assert {a.name for a in items} == set(available_activators())


def test_resolve_activators_all_keyword() -> None:
    items = resolve_activators(["all"])
    assert {a.name for a in items} == set(available_activators())


def test_resolve_activators_substring() -> None:
    items = resolve_activators(["bash,fish"])
    names = {a.name for a in items}
    assert names == {"bash", "fish"}


def test_resolve_activators_negative_removes() -> None:
    items = resolve_activators(["-fish"])
    names = {a.name for a in items}
    assert "fish" not in names
    assert "bash" in names


def test_resolve_activators_unknown_raises() -> None:
    with pytest.raises(ConfigError):
        resolve_activators(["bogus"])


def test_resolve_activators_instances_have_templates() -> None:
    items = resolve_activators(["bash"])
    assert all(isinstance(a, Activator) for a in items)
    assert all(a.templates for a in items)


# -- per-activator generation --------------------------------------------------


@pytest.mark.parametrize(
    "activator_cls, file_name",
    [
        (BashActivator, "activate"),
        (CShActivator, "activate.csh"),
        (FishActivator, "activate.fish"),
        (NushellActivator, "activate.nu"),
        (PowerShellActivator, "Activate.ps1"),
        (PythonActivator, "activate_this.py"),
    ],
)
def test_activator_generates_file(
    tmp_path: Path, activator_cls: type[Activator], file_name: str
) -> None:
    ctx = _ctx(tmp_path)
    written = activator_cls().generate(ctx)
    assert written
    target = ctx.bin_path / file_name
    assert target.exists()
    assert "__VENV_" not in target.read_text(encoding="utf-8")


def test_bash_activator_substitutes_prompt(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    BashActivator().generate(ctx)
    body = (ctx.bin_path / "activate").read_text(encoding="utf-8")
    assert "myproj" in body
    # The env dir is substituted as the VIRTUAL_ENV value; whether it
    # gets quoted depends on shlex.quote rules (e.g. drive-letter paths
    # on Windows aren't quoted). Just make sure the placeholders are gone.
    assert "__VENV_DIR_SH__" not in body
    assert "__VENV_BIN_PATH_SH__" not in body
    assert "__VENV_PROMPT__" not in body


def test_powershell_activator_substitutes_prompt(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    PowerShellActivator().generate(ctx)
    body = (ctx.bin_path / "Activate.ps1").read_text(encoding="utf-8")
    assert "myproj" in body


def test_batch_activator_only_on_nt(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    activator = BatchActivator()
    if os.name == "nt":
        written = activator.generate(ctx)
        assert written
        assert (ctx.bin_path / "activate.bat").exists()
    else:
        assert activator.generate(ctx) == []


def test_bash_script_is_executable_on_posix(tmp_path: Path) -> None:
    if sys.platform == "win32":
        pytest.skip("POSIX only")
    ctx = _ctx(tmp_path)
    BashActivator().generate(ctx)
    target = ctx.bin_path / "activate"
    assert target.stat().st_mode & stat.S_IXUSR


def test_python_activator_substitutes_lib_rel(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    PythonActivator().generate(ctx)
    body = (ctx.bin_path / "activate_this.py").read_text(encoding="utf-8")
    # The site-packages relative path must be substituted in
    assert "__VENV_LIB_REL__" not in body


def test_batch_activator_uses_crlf(tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("batch is only generated on Windows")
    ctx = _ctx(tmp_path)
    BatchActivator().generate(ctx)
    raw = (ctx.bin_path / "activate.bat").read_bytes()
    assert b"\r\n" in raw


def test_activator_rejects_unsubstituted_placeholders(tmp_path: Path) -> None:
    # A bogus placeholder in the template would leak through to the file.
    # Use a subclass that injects one.
    class BadActivator(Activator):
        name = "bad"
        templates = {"bad.sh": "echo __VENV_FOO__"}

    ctx = _ctx(tmp_path)
    with pytest.raises(ActivateError):
        BadActivator().generate(ctx)
