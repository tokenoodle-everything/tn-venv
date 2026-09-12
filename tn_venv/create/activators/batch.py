"""Windows batch (cmd.exe) activation scripts: activate.bat + deactivate.bat."""

from __future__ import annotations

import os

from .base import Activator

BATCH_ACTIVATE = """\
@echo off

rem This file is UTF-8 encoded, so we need to update the current code page while executing it
for /f "tokens=2 delims=:." %%a in ('"%SystemRoot%\\System32\\chcp.com"') do (
    set _OLD_CODEPAGE=%%a
)
if defined _OLD_CODEPAGE (
    "%SystemRoot%\\System32\\chcp.com" 65001 > nul
)

set "VIRTUAL_ENV=__VENV_DIR__"

if not defined PROMPT set PROMPT=$P$G

if defined _OLD_VIRTUAL_PROMPT set PROMPT=%_OLD_VIRTUAL_PROMPT%
if defined _OLD_VIRTUAL_PYTHONHOME set PYTHONHOME=%_OLD_VIRTUAL_PYTHONHOME%

set "_OLD_VIRTUAL_PROMPT=%PROMPT%"
set "PROMPT=(__VENV_PROMPT__) %PROMPT%"

if defined PYTHONHOME set _OLD_VIRTUAL_PYTHONHOME=%PYTHONHOME%
set PYTHONHOME=

if defined _OLD_VIRTUAL_PATH set PATH=%_OLD_VIRTUAL_PATH%
if not defined _OLD_VIRTUAL_PATH set _OLD_VIRTUAL_PATH=%PATH%

set "PATH=%VIRTUAL_ENV%\\__VENV_BIN_NAME__;%PATH%"
set "VIRTUAL_ENV_PROMPT=__VENV_PROMPT__"

if defined _OLD_CODEPAGE (
    "%SystemRoot%\\System32\\chcp.com" %_OLD_CODEPAGE% > nul
    set _OLD_CODEPAGE=
)
"""

BATCH_DEACTIVATE = """\
@echo off

if defined _OLD_VIRTUAL_PROMPT (
    set "PROMPT=%_OLD_VIRTUAL_PROMPT%"
)
set _OLD_VIRTUAL_PROMPT=

if defined _OLD_VIRTUAL_PYTHONHOME (
    set "PYTHONHOME=%_OLD_VIRTUAL_PYTHONHOME%"
    set _OLD_VIRTUAL_PYTHONHOME=
)

if defined _OLD_VIRTUAL_PATH (
    set "PATH=%_OLD_VIRTUAL_PATH%"
)
set _OLD_VIRTUAL_PATH=

set VIRTUAL_ENV=
set VIRTUAL_ENV_PROMPT=

:END
"""


class BatchActivator(Activator):
    name = "batch"
    templates = {
        "activate.bat": BATCH_ACTIVATE,
        "deactivate.bat": BATCH_DEACTIVATE,
    }

    def supports(self, ctx) -> bool:
        return os.name == "nt"
