"""Subprocess execution with friendly errors and debug reporting."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..errors import SubprocessError
from ..report import Reporter, SILENT


def run_cmd(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
    report: Reporter = SILENT,
    check: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    """Run *cmd* capturing output; raise :class:`SubprocessError` on failure.

    Output is echoed through the reporter at debug level so ``-vv`` shows
    exactly what pip / ensurepip said.
    """
    report.debug(f"$ {' '.join(str(c) for c in cmd)}")
    try:
        proc = subprocess.run(
            [str(c) for c in cmd],
            env=env,
            cwd=None if cwd is None else str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as exc:
        raise SubprocessError([str(c) for c in cmd], 127, str(exc)) from exc
    output = (proc.stdout or b"").decode("utf-8", errors="replace")
    if output.strip():
        for line in output.rstrip().splitlines():
            report.debug(f"  | {line}")
    if check and proc.returncode != 0:
        raise SubprocessError([str(c) for c in cmd], proc.returncode, output)
    proc.stdout = output  # type: ignore[assignment]
    return proc


def clean_pip_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for invoking the *new* venv interpreter.

    Follows stdlib venv: drop PYTHONHOME/PYTHONPATH so user settings cannot
    leak into the fresh environment; silence pip's version check and
    interactive prompts for reproducible, fast installs.
    """
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env.pop("__PYVENV_LAUNCHER__", None)  # macOS framework builds
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    env.setdefault("PIP_NO_INPUT", "1")
    if extra:
        env.update(extra)
    return env
