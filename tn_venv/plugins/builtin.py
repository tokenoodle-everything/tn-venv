"""Built-in plugins shipped with tn-venv.

Currently this package exposes exactly one plugin — :class:`VersionStampPlugin`
— which records the tn-venv release that produced an environment by
appending ``tn-venv-version = <version>`` to ``pyvenv.cfg`` after the
activation scripts have been written. This is intentionally trivial: it
exists as a worked example for plugin authors and as a smoke test that
the hook machinery fires at the right point in the pipeline.

Plugins live here (rather than beside the creator) so the plugin system
remains discoverable in ``tn_venv.plugins`` regardless of which built-in
plugins are present.
"""

from __future__ import annotations

from pathlib import Path

from ..version import __version__
from .api import HookContext, HookName, Plugin
from .registry import DEFAULT_PRIORITY

_CFG_KEY = "tn-venv-version"


class VersionStampPlugin(Plugin):
    """Write ``tn-venv-version`` into ``pyvenv.cfg`` after activators.

    Runs on the :attr:`~tn_venv.plugins.api.HookName.POST_ACTIVATORS`
    hook with the lowest priority, so user plugins can override or
    extend the recorded version.
    """

    #: Stable identifier; required by :class:`Plugin`.
    name = "version_stamp"

    def register(self, hooks) -> None:
        hooks.add(
            HookName.POST_ACTIVATORS,
            self._stamp,
            priority=DEFAULT_PRIORITY - 50,  # run after most user plugins
            plugin_name=self.name,
        )

    @staticmethod
    def _stamp(ctx: HookContext) -> None:
        cfg_path = _resolve_cfg(ctx)
        if cfg_path is None:
            return
        reporter = ctx.reporter
        try:
            _append_version_line(cfg_path, __version__)
        except OSError as exc:
            if reporter is not None:
                reporter.warn(
                    f"version_stamp plugin could not update {cfg_path}: {exc}"
                )
            return
        if reporter is not None:
            reporter.debug(f"stamped {cfg_path.name} with tn-venv version")


def _resolve_cfg(ctx: HookContext) -> Path | None:
    """Find the ``pyvenv.cfg`` path from the hook context.

    Uses :attr:`HookContext.data` first (set by other plugins or by the
    session); falls back to walking ``ctx.result`` if a session result
    is already populated (it isn't on ``POST_ACTIVATORS``); finally
    inspects the *options* attached to the context. Returning ``None``
    signals "I have no idea where the cfg lives" — the plugin then
    stays silent rather than guessing.
    """
    if ctx.data is not None:
        candidate = ctx.data.get("cfg_path")
        if isinstance(candidate, Path):
            return candidate
    if ctx.result is not None:
        env_dir = ctx.result.env_dir
        if env_dir is not None:
            return Path(env_dir) / "pyvenv.cfg"
    return None


def _append_version_line(cfg_path: Path, version: str) -> None:
    """Append ``tn-venv-version = <version>`` to ``cfg_path``.

    Idempotent: if the key is already present (with any value) the file
    is left alone. Otherwise the new key is appended on its own line.
    """
    if not cfg_path.exists():
        return
    text = cfg_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith(f"{_CFG_KEY} "):
            return
    sep = "" if text.endswith("\n") else "\n"
    cfg_path.write_text(
        text + sep + f"{_CFG_KEY} = {version}\n",
        encoding="utf-8",
    )


__all__ = ["VersionStampPlugin"]
