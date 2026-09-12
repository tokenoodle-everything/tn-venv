"""Activation script generation framework."""

from __future__ import annotations

import os
import shlex
from pathlib import Path

from ...errors import ActivateError
from ...util.path import write_text
from ..context import CreatorContext


class Activator:
    """Base class for activation-script generators.

    Subclasses define ``name`` and ``templates``: a mapping of output file
    name → template text using ``__VENV_*__`` placeholders.
    """

    name: str = ""
    templates: dict[str, str] = {}
    #: file names (relative to bin dir) that should be chmod +x on POSIX
    executable_names: tuple[str, ...] = ()

    def supports(self, ctx: CreatorContext) -> bool:
        """Whether this activator makes sense for the environment."""
        return True

    # -- placeholder substitution ------------------------------------------
    def replacements(self, ctx: CreatorContext) -> dict[str, str]:
        env_dir = ctx.env_var_dir()
        bin_name = ctx.bin_name
        exe = str(ctx.env_exe)
        prompt = ctx.prompt
        return {
            "__VENV_DIR__": env_dir,
            "__VENV_NAME__": ctx.env_name,
            "__VENV_PROMPT__": prompt,
            "__VENV_BIN_NAME__": bin_name,
            "__VENV_BIN_NAME_SLASH__": bin_name.replace(os.sep, "/"),
            "__VENV_PYTHON__": exe,
            "__VENV_DIR_SH__": self._sh_quote(self._posix_path(env_dir)),
            "__VENV_BIN_PATH_SH__": self._sh_quote(
                self._posix_path(env_dir) + "/" + bin_name.replace(os.sep, "/")
            ),
            "__VENV_PROMPT_SH__": self._sh_quote(prompt),
            "__VENV_DIR_PS__": self._ps_quote(env_dir),
            "__VENV_PROMPT_PS__": self._ps_quote(prompt),
            "__VENV_DIR_FISH__": self._fish_quote(env_dir),
            "__VENV_PROMPT_FISH__": self._fish_quote(prompt),
        }

    @staticmethod
    def _posix_path(p: str) -> str:
        # git-bash / msys cope best with forward slashes
        return p.replace("\\", "/") if os.name == "nt" else p

    @staticmethod
    def _sh_quote(s: str) -> str:
        return shlex.quote(s)

    @staticmethod
    def _ps_quote(s: str) -> str:
        return "'" + s.replace("'", "''") + "'"

    @staticmethod
    def _fish_quote(s: str) -> str:
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"

    # -- generation ------------------------------------------------------------
    def generate(self, ctx: CreatorContext) -> list[Path]:
        if not self.supports(ctx):
            return []
        repl = self.replacements(ctx)
        written: list[Path] = []
        for file_name, template in self.templates.items():
            text = template
            for key, value in repl.items():
                text = text.replace(key, value)
            if "__VENV_" in text:
                raise ActivateError(
                    f"{self.name}: unsubstituted placeholder in {file_name}"
                )
            dest = ctx.bin_path / file_name
            newline = "\r\n" if file_name.endswith(".bat") else "\n"
            executable = os.name != "nt" and file_name in self.executable_names
            write_text(dest, text, executable=executable, newline=newline)
            written.append(dest)
        return written
