"""Tests for the built-in VersionStampPlugin."""

from __future__ import annotations

from pathlib import Path

import pytest

from tn_venv.plugins import HookContext, HookName, VersionStampPlugin, load_plugins
from tn_venv.plugins.builtin import (
    _CFG_KEY,
    _append_version_line,
    _resolve_cfg,
)
from tn_venv.report import Reporter
from tn_venv.version import __version__


# -- _append_version_line ---------------------------------------------------


def test_append_version_line_creates_key(tmp_path: Path) -> None:
    cfg = tmp_path / "pyvenv.cfg"
    cfg.write_text("home = /usr/bin\n", encoding="utf-8")
    _append_version_line(cfg, "1.2.3")
    text = cfg.read_text(encoding="utf-8")
    assert text.startswith("home = /usr/bin")
    assert f"{_CFG_KEY} = 1.2.3" in text


def test_append_version_line_is_idempotent(tmp_path: Path) -> None:
    cfg = tmp_path / "pyvenv.cfg"
    cfg.write_text(
        f"home = /usr/bin\n{_CFG_KEY} = 0.1.0\n",
        encoding="utf-8",
    )
    _append_version_line(cfg, "9.9.9")
    text = cfg.read_text(encoding="utf-8")
    # The first value wins; the second call does not overwrite it.
    assert text.count(_CFG_KEY) == 1
    assert f"{_CFG_KEY} = 0.1.0" in text


def test_append_version_line_handles_missing_trailing_newline(
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "pyvenv.cfg"
    cfg.write_text("home = /usr/bin", encoding="utf-8")
    _append_version_line(cfg, "1.0")
    text = cfg.read_text(encoding="utf-8")
    assert f"{_CFG_KEY} = 1.0" in text


def test_append_version_line_silent_on_missing_file(tmp_path: Path) -> None:
    cfg = tmp_path / "pyvenv.cfg"
    _append_version_line(cfg, "1.0")
    assert not cfg.exists()


# -- _resolve_cfg -----------------------------------------------------------


def test_resolve_cfg_uses_data_dict(tmp_path: Path) -> None:
    cfg = tmp_path / "pyvenv.cfg"
    ctx = HookContext(data={"cfg_path": cfg})
    assert _resolve_cfg(ctx) == cfg


def test_resolve_cfg_falls_back_to_result_env_dir(tmp_path: Path) -> None:
    from dataclasses import dataclass

    @dataclass
    class _FakeResult:
        env_dir: Path

    ctx = HookContext(data={}, result=_FakeResult(env_dir=tmp_path))
    assert _resolve_cfg(ctx) == tmp_path / "pyvenv.cfg"


def test_resolve_cfg_returns_none_without_info() -> None:
    ctx = HookContext()
    assert _resolve_cfg(ctx) is None


# -- VersionStampPlugin integration -----------------------------------------


def _run_registrar() -> "callable":
    """Return the bound hook function the plugin registered."""
    from tn_venv.plugins import HookRegistry

    plugin = VersionStampPlugin()
    registry = HookRegistry()
    plugin.register(registry)
    return registry.listeners(HookName.POST_ACTIVATORS)[0]


def test_version_stamp_appends_current_version(tmp_path: Path) -> None:
    cfg = tmp_path / "pyvenv.cfg"
    cfg.write_text("home = /usr/bin\n", encoding="utf-8")
    ctx = HookContext(data={"cfg_path": cfg})
    _run_registrar()(ctx)
    assert f"{_CFG_KEY} = {__version__}" in cfg.read_text(encoding="utf-8")


def test_version_stamp_silently_skips_missing_cfg(tmp_path: Path) -> None:
    ctx = HookContext(data={"cfg_path": tmp_path / "pyvenv.cfg"})
    # Should not raise even though the file does not exist.
    _run_registrar()(ctx)


def test_version_stamp_silently_skips_when_ctx_has_no_paths() -> None:
    ctx = HookContext()
    # No cfg, no result: stays silent.
    _run_registrar()(ctx)


def test_version_stamp_reports_warning_on_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "pyvenv.cfg"
    cfg.write_text("home = /usr/bin\n", encoding="utf-8")
    reporter = Reporter(verbosity=0)

    def _boom(_cfg_path, _version):
        raise OSError("permission denied")

    monkeypatch.setattr("tn_venv.plugins.builtin._append_version_line", _boom)
    ctx = HookContext(data={"cfg_path": cfg}, reporter=reporter)
    _run_registrar()(ctx)
    # Should not raise; the reporter swallowed the failure.


def test_load_plugins_includes_builtin_by_default() -> None:
    registry = load_plugins(Reporter(verbosity=0))
    callables = registry.listeners(HookName.POST_ACTIVATORS)
    qualnames = [fn.__qualname__ for fn in callables]
    assert any(q == "VersionStampPlugin._stamp" for q in qualnames)
