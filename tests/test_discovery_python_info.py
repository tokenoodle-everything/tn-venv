"""Tests for tn_venv.discovery.python_info."""

from __future__ import annotations

import sys

import pytest

from tn_venv.discovery.python_info import (
    InterpreterSpec,
    PythonInfo,
    clear_probe_cache,
    parse_spec,
)
from tn_venv.errors import DiscoverError


@pytest.fixture(autouse=True)
def _clear_probe_cache() -> None:
    clear_probe_cache()


def test_python_info_from_current_shape(current_python: PythonInfo) -> None:
    assert current_python.executable
    assert current_python.base_executable
    assert isinstance(current_python.version_info, tuple)
    assert len(current_python.version_info) == 3
    assert current_python.version_str == ".".join(
        str(i) for i in current_python.version_info
    )
    assert current_python.major_minor == f"{sys.version_info[0]}.{sys.version_info[1]}"


def test_python_info_bits_matches_sys() -> None:
    info = PythonInfo.from_current()
    assert info.bits in (32, 64)
    assert info.is_64 is (info.bits == 64)


def test_python_info_is_total_orderable() -> None:
    a = PythonInfo(
        executable="x",
        base_executable="x",
        version_info=(3, 11, 0),
    )
    b = PythonInfo(
        executable="y",
        base_executable="y",
        version_info=(3, 12, 0),
    )
    assert a < b
    assert b > a
    assert a <= a
    assert b >= b


def test_python_info_str_includes_version() -> None:
    info = PythonInfo(
        executable="/x",
        base_executable="/x",
        version_info=(3, 12, 1),
        implementation="cpython",
    )
    assert "3.12.1" in str(info)


def test_python_info_is_frozen() -> None:
    info = PythonInfo.from_current()
    with pytest.raises((AttributeError, Exception)):
        info.executable = "nope"  # type: ignore[misc]


# -- parse_spec ----------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("3", InterpreterSpec(major=3, raw="3")),
        ("3.12", InterpreterSpec(major=3, minor=12, raw="3.12")),
        ("3.12.1", InterpreterSpec(major=3, minor=12, patch=1, raw="3.12.1")),
        ("3.11-64", InterpreterSpec(major=3, minor=11, arch=64, raw="3.11-64")),
        (
            "python3.12",
            InterpreterSpec(
                implementation="python", major=3, minor=12, raw="python3.12"
            ),
        ),
        (
            "pypy3.10",
            InterpreterSpec(implementation="pypy", major=3, minor=10, raw="pypy3.10"),
        ),
        (
            "CPython-3.13",
            InterpreterSpec(
                implementation="cpython", major=3, minor=13, raw="CPython-3.13"
            ),
        ),
    ],
)
def test_parse_spec(raw: str, expected: InterpreterSpec) -> None:
    spec = parse_spec(raw)
    assert spec is not None
    assert spec.major == expected.major
    assert spec.minor == expected.minor
    assert spec.patch == expected.patch
    assert spec.arch == expected.arch
    assert spec.implementation == expected.implementation


@pytest.mark.parametrize("raw", ["/some/path", "python3.12.exe", "weird name", ""])
def test_parse_spec_returns_none_for_non_version(raw: str) -> None:
    assert parse_spec(raw) is None


def test_interpreter_spec_describe() -> None:
    s = InterpreterSpec(implementation="cpython", major=3, minor=12)
    assert s.describe() == "cpython-3.12"
    s2 = InterpreterSpec(implementation="pypy", major=3, minor=10, patch=5)
    assert s2.describe() == "pypy-3.10.5"
    s3 = InterpreterSpec(implementation=None, major=3)
    assert s3.describe() == "python-3"
    s4 = InterpreterSpec()
    assert s4.is_any


# -- matches ------------------------------------------------------------------


def _info(version_info=(3, 12, 0), implementation="cpython") -> PythonInfo:
    return PythonInfo(
        executable="/x",
        base_executable="/x",
        version_info=version_info,
        implementation=implementation,
    )


def test_matches_any_when_no_version_constraint() -> None:
    info = _info()
    assert info.matches(InterpreterSpec())


def test_matches_major_minor_patch() -> None:
    info = _info()
    assert info.matches(InterpreterSpec(major=3))
    assert info.matches(InterpreterSpec(major=3, minor=12))
    assert info.matches(InterpreterSpec(major=3, minor=12, patch=0))
    assert not info.matches(InterpreterSpec(major=4))
    assert not info.matches(InterpreterSpec(major=3, minor=13))


def test_matches_arch() -> None:
    info = _info()
    assert info.matches(InterpreterSpec(arch=info.bits))
    assert not info.matches(InterpreterSpec(arch=32 if info.bits == 64 else 64))


def test_matches_implementation() -> None:
    cpy = _info(implementation="cpython")
    pypy = _info(implementation="pypy")
    assert cpy.matches(InterpreterSpec(implementation="cpython"))
    assert not cpy.matches(InterpreterSpec(implementation="pypy"))
    # "python" maps to cpython
    assert cpy.matches(InterpreterSpec(implementation="python"))
    assert not pypy.matches(InterpreterSpec(implementation="python"))
    assert not pypy.matches(InterpreterSpec(implementation="py"))


def test_from_exe_missing_raises() -> None:
    with pytest.raises(DiscoverError):
        PythonInfo.from_exe("/this/path/does/not/exist/bin/python")


def test_from_exe_current_probes_current() -> None:
    info = PythonInfo.from_exe(sys.executable)
    assert info.version_info == sys.version_info[:3]


def test_from_exe_caches_results() -> None:
    a = PythonInfo.from_exe(sys.executable)
    b = PythonInfo.from_exe(sys.executable)
    # Cache returns the same object for identical paths
    assert a is b


def test_from_exe_bypass_cache() -> None:
    a = PythonInfo.from_exe(sys.executable)
    b = PythonInfo.from_exe(sys.executable, use_cache=False)
    # Same logical data but distinct objects
    assert a == b
    assert a is not b
