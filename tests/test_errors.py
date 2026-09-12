"""Tests for the tn-venv exception hierarchy."""

from __future__ import annotations

import pytest

from tn_venv.errors import (
    ActivateError,
    ConfigError,
    CreateError,
    DiscoverError,
    InterpreterNotFoundError,
    LockError,
    SeedError,
    SubprocessError,
    TNError,
)


def test_tnerror_is_exception() -> None:
    assert issubclass(TNError, Exception)


@pytest.mark.parametrize(
    "cls",
    [
        ConfigError,
        DiscoverError,
        InterpreterNotFoundError,
        CreateError,
        ActivateError,
        SeedError,
        LockError,
        SubprocessError,
    ],
)
def test_all_errors_inherit_from_tnerror(cls: type[Exception]) -> None:
    assert issubclass(cls, TNError)


def test_interpreter_not_found_no_candidates() -> None:
    exc = InterpreterNotFoundError("3.99")
    assert exc.spec == "3.99"
    assert exc.tried == []
    assert "3.99" in str(exc)
    assert "candidates probed" not in str(exc)


def test_interpreter_not_found_with_candidates() -> None:
    exc = InterpreterNotFoundError("3.99", tried=["/a/python", "/b/python"])
    assert exc.tried == ["/a/python", "/b/python"]
    msg = str(exc)
    assert "/a/python" in msg
    assert "/b/python" in msg
    assert "candidates probed" in msg


def test_subprocess_error_stores_fields() -> None:
    exc = SubprocessError(["python", "-c", "boom"], 1, "Traceback")
    assert exc.cmd == ["python", "-c", "boom"]
    assert exc.returncode == 1
    assert exc.output == "Traceback"
    msg = str(exc)
    assert "exit code 1" in msg
    assert "Traceback" in msg
    assert "python -c boom" in msg


def test_subprocess_error_without_output() -> None:
    exc = SubprocessError(["python"], 2)
    assert exc.output == ""
    assert "output" not in str(exc)


def test_config_and_create_are_distinct() -> None:
    # catch handlers can tell config errors apart from runtime ones
    assert not issubclass(CreateError, ConfigError)
    assert not issubclass(SeedError, CreateError)


def test_interpreter_not_found_is_discover_error() -> None:
    assert issubclass(InterpreterNotFoundError, DiscoverError)
