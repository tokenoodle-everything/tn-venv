"""tn-venv — create Python virtual environments with one command.

Public API::

    from tn_venv import create_venv
    result = create_venv(".venv", python="3.12", packages=["requests"])

Command line::

    tn-venv [OPTIONS] [DEST]
    python -m tn_venv [OPTIONS] [DEST]
"""

from __future__ import annotations

from .errors import (
    ActivateError,
    ConfigError,
    CreateError,
    DiscoverError,
    InterpreterNotFoundError,
    SeedError,
    TNError,
)
from .session import Options, SessionResult, create_venv
from .version import __version__, __version_tuple__


def cli_run(args: list[str] | None = None, **kwargs) -> int:
    """Run the CLI programmatically; returns the process exit code."""
    from .cli import cli_run as _cli_run

    return _cli_run(args, **kwargs)


__all__ = [
    "__version__",
    "__version_tuple__",
    "create_venv",
    "cli_run",
    "Options",
    "SessionResult",
    "TNError",
    "ConfigError",
    "CreateError",
    "DiscoverError",
    "InterpreterNotFoundError",
    "SeedError",
    "ActivateError",
]
