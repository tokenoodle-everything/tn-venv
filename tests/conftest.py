"""Shared fixtures for the tn-venv test-suite."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tn_venv.discovery import PythonInfo
from tn_venv.report import Reporter


@pytest.fixture(scope="session")
def current_python() -> PythonInfo:
    return PythonInfo.from_current()


@pytest.fixture()
def reporter() -> Reporter:
    # silent but keeps code paths identical to the CLI
    return Reporter(verbosity=-1, color=False)


@pytest.fixture()
def run_env():
    """Run a command inside a created environment, returning CompletedProcess."""

    def _run(exe: Path, *args: str, timeout: float = 120):
        return subprocess.run(
            [str(exe), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    return _run


@pytest.fixture(autouse=True)
def _no_config_leak(monkeypatch, tmp_path):
    """Tests must not pick up config files / env vars from the real world."""
    empty = tmp_path / "empty-tn-venv.ini"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("TN_VENV_CONFIG_FILE", str(empty))
    for key in list(os.environ):
        if key.startswith("TN_VENV_") and key != "TN_VENV_CONFIG_FILE":
            monkeypatch.delenv(key, raising=False)
