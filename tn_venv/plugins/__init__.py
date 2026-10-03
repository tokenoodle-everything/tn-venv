"""Plugin system for tn-venv.

A *plugin* is a :class:`Plugin` subclass that registers one or more hook
callbacks on a :class:`HookRegistry`. The session pipeline emits hooks at
well-defined points (see :class:`HookName`) and every registered callback
runs in priority order. Plugins are discovered through entry points
(``tn_venv.plugins`` group), the ``TN_VENV_PLUGINS`` environment
variable, and built-ins shipped with tn-venv itself.

Quick start::

    from tn_venv.plugins import Plugin, HookName, HookContext

    class TimestampPlugin(Plugin):
        name = "timestamp"

        def register(self, hooks):
            hooks.add(HookName.SESSION_START, self._stamp)

        def _stamp(self, ctx: HookContext) -> None:
            ctx.data["started_at"] = __import__("time").time()

See :mod:`tn_venv.plugins.api` for the contract, and
:mod:`tn_venv.plugins.loader` for discovery rules.
"""

from __future__ import annotations

from .api import (
    PLUGIN_ENTRY_POINT,
    PLUGIN_ENV_VAR,
    HookContext,
    HookFn,
    HookName,
    Plugin,
)
from .builtin import VersionStampPlugin
from .loader import load_plugins, parse_plugin_spec, require_plugin
from .registry import DEFAULT_PRIORITY, HookRegistry

__all__ = [
    "Plugin",
    "HookContext",
    "HookName",
    "HookFn",
    "HookRegistry",
    "DEFAULT_PRIORITY",
    "PLUGIN_ENTRY_POINT",
    "PLUGIN_ENV_VAR",
    "VersionStampPlugin",
    "load_plugins",
    "parse_plugin_spec",
    "require_plugin",
]

