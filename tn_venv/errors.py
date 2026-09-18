"""Exception hierarchy for tn-venv.

Every error raised intentionally by tn-venv derives from :class:`TnVenvError`,
so callers (and the CLI) can distinguish *our* failures from unexpected
programmer errors.
"""

from __future__ import annotations

__all__ = [
    "TNError",
    "TnVenvError",
    "ConfigError",
    "DiscoverError",
    "CreateError",
    "ActivateError",
    "SeedError",
    "LockError",
    "InterpreterNotFoundError",
    "SubprocessError",
]


class TnVenvError(Exception):
    """Base class for all tn-venv errors."""


TNError = TnVenvError  # backport


class ConfigError(TnVenvError):
    """Invalid configuration (CLI flag, env var, or config file)."""


class DiscoverError(TnVenvError):
    """Failure while probing a Python interpreter."""


class InterpreterNotFoundError(DiscoverError):
    """No interpreter matched the requested spec."""

    def __init__(self, spec: str, tried: list[str] | None = None) -> None:
        self.spec = spec
        self.tried = tried or []
        hint = ""
        if self.tried:
            hint = "\ncandidates probed:\n  " + "\n  ".join(self.tried)
        super().__init__(f"no Python interpreter found for spec {spec!r}{hint}")


class CreateError(TnVenvError):
    """Failure while laying down the virtual environment files."""


class ActivateError(TnVenvError):
    """Failure while generating activation scripts."""


class SeedError(TnVenvError):
    """Failure while installing pip / setuptools / wheel / packages."""


class LockError(TnVenvError):
    """Could not acquire the creation lock in time."""


class SubprocessError(TnVenvError):
    """A helper subprocess exited with a non-zero status."""

    def __init__(self, cmd: list[str], returncode: int, output: str = "") -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.output = output
        rendered = " ".join(cmd)
        message = f"command failed with exit code {returncode}: {rendered}"
        if output:
            message += f"\n--- output ---\n{output.rstrip()}\n--------------"
        super().__init__(message)
