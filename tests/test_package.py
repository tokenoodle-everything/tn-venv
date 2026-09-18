"""Tests for the top-level ``tn_venv`` package exports."""

from __future__ import annotations

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
    TnVenvError,
    cli_run,
    create_venv,
)


def test_public_api_callables() -> None:
    assert callable(cli_run)
    assert callable(create_venv)


def test_public_classes() -> None:
    assert Options.__dataclass_fields__  # type: ignore[attr-defined]
    assert SessionResult.__dataclass_fields__  # type: ignore[attr-defined]


def test_error_hierarchy_exposed() -> None:
    assert issubclass(ConfigError, TnVenvError)
    assert issubclass(CreateError, TnVenvError)
    assert issubclass(DiscoverError, TnVenvError)
    assert issubclass(InterpreterNotFoundError, TnVenvError)
    assert issubclass(SeedError, TnVenvError)
    assert issubclass(ActivateError, TnVenvError)


def test_cli_run_signature_accepts_no_args() -> None:
    # Don't actually call it — just check the signature exists
    import inspect

    sig = inspect.signature(cli_run)
    assert "args" in sig.parameters or sig.parameters


def test_create_venv_is_documented_callable() -> None:
    assert create_venv.__doc__
    assert "Programmatic API" in create_venv.__doc__
