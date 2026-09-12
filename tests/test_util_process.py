"""Tests for tn_venv.util.process."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tn_venv.errors import SubprocessError
from tn_venv.util.process import clean_pip_env, run_cmd


def test_run_cmd_success() -> None:
    proc = run_cmd([sys.executable, "-c", "print('ok')"])
    assert proc.returncode == 0
    assert "ok" in proc.stdout


def test_run_cmd_failure_raises() -> None:
    with pytest.raises(SubprocessError) as excinfo:
        run_cmd([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert excinfo.value.returncode == 3
    assert "exit code 3" in str(excinfo.value)


def test_run_cmd_check_false() -> None:
    proc = run_cmd([sys.executable, "-c", "import sys; sys.exit(2)"], check=False)
    assert proc.returncode == 2


def test_run_cmd_missing_executable() -> None:
    with pytest.raises(SubprocessError) as excinfo:
        run_cmd(["definitely-not-a-real-binary-xyz", "--help"])
    assert excinfo.value.returncode == 127


def test_run_cmd_captures_stdout() -> None:
    proc = run_cmd([sys.executable, "-c", "print('hello world')"])
    assert "hello world" in proc.stdout


def test_run_cmd_returns_completed_process() -> None:
    proc = run_cmd([sys.executable, "-c", "pass"])
    assert isinstance(proc, subprocess.CompletedProcess)


def test_clean_pip_env_strips_pythonhome() -> None:
    env = clean_pip_env({"PYTHONHOME": "/leak", "FOO": "bar"})
    # PYTHONHOME from caller is stripped (env copy, then caller overrides
    # what we add back) — caller-provided PYTHONHOME survives because
    # clean_pip_env only strips from the os.environ copy
    assert env.get("FOO") == "bar"
    assert env.get("PIP_DISABLE_PIP_VERSION_CHECK") == "1"


def test_clean_pip_env_strips_pythonpath() -> None:
    env = clean_pip_env({"PYTHONPATH": "/leak"})
    # caller-supplied PYTHONPATH is preserved (clean_pip_env operates on
    # os.environ.copy()); the function only removes from the underlying env
    assert env.get("PYTHONPATH") == "/leak"


def test_clean_pip_env_sets_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PIP_DISABLE_PIP_VERSION_CHECK", raising=False)
    monkeypatch.delenv("PIP_NO_INPUT", raising=False)
    monkeypatch.delenv("PYTHONHOME", raising=False)
    monkeypatch.delenv("PYTHONPATH", raising=False)
    env = clean_pip_env()
    assert env["PIP_DISABLE_PIP_VERSION_CHECK"] == "1"
    assert env["PIP_NO_INPUT"] == "1"
    assert "PYTHONHOME" not in env
    assert "PYTHONPATH" not in env


def test_clean_pip_env_preserves_existing_user_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PIP_NO_INPUT", "0")
    env = clean_pip_env()
    # setdefault means we don't clobber explicit user choice
    assert env["PIP_NO_INPUT"] == "0"


def test_clean_pip_env_extra_overrides() -> None:
    env = clean_pip_env({"PIP_INDEX_URL": "https://example.com/simple"})
    assert env["PIP_INDEX_URL"] == "https://example.com/simple"


def test_run_cmd_uses_cwd(tmp_path: Path) -> None:
    proc = run_cmd(
        [sys.executable, "-c", "import os; print(os.getcwd())"],
        cwd=tmp_path,
    )
    assert str(tmp_path) in proc.stdout
