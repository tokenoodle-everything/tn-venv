"""Tests for the top-level ``tn_venv`` package exports."""

from __future__ import annotations

import pytest

import tn_venv
from tn_venv import (
    ActivateError,
    ConfigError,
    CreateError,
    DiscoverError,
    InterpreterNotFoundError,
    Options,
    SeedError,
    SessionResult,
    TNError,
    cli_run,
    create_venv,
)


def test_version_exports() -> None:
    assert tn_venv.__version__ == "0.1.0"
    assert tn_venv.__version_tuple__ == (0, 1, 0)


def test_public_api_callables() -> None:
    assert callable(cli_run)
    assert callable(create_venv)


def test_public_classes() -> None:
    assert Options.__dataclass_fields__  # type: ignore[attr-defined]
    assert SessionResult.__dataclass_fields__  # type: ignore[attr-defined]


def test_error_hierarchy_exposed() -> None:
    assert issubclass(ConfigError, TNError)
    assert issubclass(CreateError, TNError)
    assert issubclass(DiscoverError, TNError)
    assert issubclass(InterpreterNotFoundError, TNError)
    assert issubclass(SeedError, TNError)
    assert issubclass(ActivateError, TNError)


def test_cli_run_signature_accepts_no_args() -> None:
    # Don't actually call it — just check the signature exists
    import inspect

    sig = inspect.signature(cli_run)
    assert "args" in sig.parameters or sig.parameters


def test_create_venv_is_documented_callable() -> None:
    assert create_venv.__doc__
    assert "Programmatic API" in create_venv.__doc__
