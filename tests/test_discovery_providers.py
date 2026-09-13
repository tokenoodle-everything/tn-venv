"""Tests for tn_venv.discovery.providers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tn_venv.discovery.providers import (
    ALL_PROVIDERS,
    Candidate,
    current_python,
    iter_candidates,
    launcher_pythons,
    path_pythons,
    registry_pythons,
    uv_pythons,
)


def test_current_python_yields_current_executable() -> None:
    items = list(current_python())
    assert items == [Candidate("current", sys.executable)]


def test_candidate_is_named_tuple() -> None:
    c = Candidate("PATH", "/x")
    assert c.source == "PATH"
    assert c.executable == "/x"


def test_path_pythons_finds_python3(monkeypatch: pytest.MonkeyPatch) -> None:
    name = "python3.exe" if sys.platform == "win32" else "python3"
    fake = "/fake/" + name
    monkeypatch.setattr("shutil.which", lambda n: fake if n == name else None)
    found = list(path_pythons())
    assert any(c.executable == fake for c in found)


def test_path_pythons_hint_filters_to_named(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    def fake_which(name: str) -> str | None:
        called.append(name)
        if name == "python3.13":
            return "/fake/python3.13"
        return None

    monkeypatch.setattr("shutil.which", fake_which)
    found = list(path_pythons("python3.13"))
    assert called == ["python3.13"]
    assert any(c.executable == "/fake/python3.13" for c in found)


def test_path_pythons_deduplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = "/fake/python"
    # On POSIX the defaults are python3 / python / python3.X / pypy3;
    # on Windows they are python.exe / python3.exe / pythonw.exe.
    if sys.platform == "win32":
        aliases = {"python.exe", "python3.exe"}
    else:
        aliases = {"python3", "python"}
    monkeypatch.setattr("shutil.which", lambda name: fake if name in aliases else None)
    seen_sources = [c.executable for c in path_pythons()]
    assert seen_sources.count(fake) == 1


def test_iter_candidates_deduplicates_across_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    same = sys.executable

    def fake_which(name: str) -> str | None:
        return same if name.startswith("python") else None

    monkeypatch.setattr("shutil.which", fake_which)
    paths = [c.executable for c in iter_candidates()]
    # current_python + path_pythons all collapse to the same executable
    assert paths.count(same) == 1


def test_iter_candidates_handles_broken_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A provider that raises must not crash discovery
    def broken():
        raise RuntimeError("nope")
        yield  # pragma: no cover

    # Patch ALL_PROVIDERS to start with the broken one
    monkeypatch.setattr(
        "tn_venv.discovery.providers.ALL_PROVIDERS", (broken, current_python)
    )
    items = list(iter_candidates())
    assert any(c.source == "current" for c in items)


def test_uv_pythons_no_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Force every root uv_pythons might scan to a non-existent path.
    # On Windows: APPDATA is the additional root.
    # On POSIX: HOME controls ~/.local/share/uv/python.
    fake_root = tmp_path / "no-such-uv-root"
    monkeypatch.setenv("UV_PYTHON_INSTALL_DIR", str(fake_root))
    monkeypatch.setenv("APPDATA", str(fake_root))
    monkeypatch.setenv("HOME", str(fake_root))
    # Path.home() may cache; patch it directly.
    monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: fake_root))
    assert list(uv_pythons()) == []


def test_uv_pythons_finds_executables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    uv = tmp_path / "uvroot"
    py = uv / "cpython-3.12.0"
    py.mkdir(parents=True)
    if sys.platform == "win32":
        (py / "python.exe").write_bytes(b"")
    else:
        (py / "bin").mkdir()
        (py / "bin" / "python3").write_bytes(b"")
    monkeypatch.setenv("UV_PYTHON_INSTALL_DIR", str(uv))
    items = list(uv_pythons())
    assert any("cpython-3.12.0" in c.source for c in items)


def test_uv_pythons_iterdir_failure_is_silent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    uv = tmp_path / "uv"
    uv.mkdir()
    monkeypatch.setenv("UV_PYTHON_INSTALL_DIR", str(uv))

    def boom(_path):
        raise OSError("denied")

    monkeypatch.setattr("pathlib.Path.iterdir", boom)
    assert list(uv_pythons()) == []


def test_registry_pythons_is_iterable() -> None:
    # Just exercise the function — on non-Windows it yields nothing
    list(registry_pythons())


def test_launcher_pythons_is_iterable() -> None:
    list(launcher_pythons())


def test_all_providers_is_non_empty() -> None:
    assert len(ALL_PROVIDERS) >= 3
