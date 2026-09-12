"""Tests for tn_venv.discovery top-level interface."""

from __future__ import annotations

import sys

import pytest

from tn_venv.discovery import (
    PythonInfo,
    clear_probe_cache,
    discover,
    discover_all,
    parse_spec,
)
from tn_venv.errors import DiscoverError, InterpreterNotFoundError


@pytest.fixture(autouse=True)
def _clear() -> None:
    clear_probe_cache()


def test_discover_none_uses_current() -> None:
    info = discover()
    assert info.executable == sys.executable


def test_discover_string_spec_single() -> None:
    info = discover("3")
    assert info.version_info[0] == 3


def test_discover_list_specs() -> None:
    info = discover(["3", "3.12"])
    assert info.version_info[0] == 3


def test_discover_skips_empty_specs() -> None:
    info = discover(["", "3"])
    assert info.version_info[0] == 3


def test_discover_explicit_path() -> None:
    info = discover(sys.executable)
    assert info.executable.endswith("python.exe") or info.executable.endswith("python")


def test_discover_no_match_raises() -> None:
    with pytest.raises(InterpreterNotFoundError) as excinfo:
        discover("99.99.99")
    assert "99.99.99" in str(excinfo.value)


def test_discover_first_spec_used_when_found() -> None:
    info = discover(["3", "99.99.99"])
    assert info.version_info[0] == 3


def test_discover_invalid_spec_does_not_match_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(InterpreterNotFoundError):
        discover("no-such-interpreter-xyz")


def test_discover_all_returns_current_at_minimum() -> None:
    found = discover_all()
    executables = [info.executable for info, _src in found]
    # The running interpreter is always a candidate
    assert sys.executable in executables


def test_discover_all_sorted_newest_first() -> None:
    found = discover_all()
    versions = [info.version_info for info, _src in found]
    assert versions == sorted(versions, reverse=True)


def test_parse_spec_round_trip() -> None:
    spec = parse_spec("3.12.1")
    assert spec is not None
    assert spec.major == 3
    assert spec.minor == 12
    assert spec.patch == 1


def test_discover_collects_candidate_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    # Make every spec produce a candidate error
    from tn_venv import discovery as mod

    def fake_discover_one(raw, *, report):
        raise DiscoverError(f"cannot probe {raw}")

    monkeypatch.setattr(mod, "_discover_one", fake_discover_one)
    with pytest.raises(InterpreterNotFoundError) as excinfo:
        discover(["a", "b"])
    assert "a" in excinfo.value.tried[0]
    assert "b" in excinfo.value.tried[1]


def test_python_info_is_exported() -> None:
    assert PythonInfo is not None
