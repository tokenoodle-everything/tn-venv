"""Public types for the plugin system.

Plugins are objects that subclass :class:`Plugin` and register one or more
hook callbacks on a :class:`~tn_venv.plugins.registry.HookRegistry`. They
are discovered via Python *entry points* in the ``tn_venv.plugins`` group
or via the ``TN_VENV_PLUGINS`` environment variable.

Hooks
-----

The hooks emitted by ``tn_venv.session.run_session`` are:

``session_start``
    Fired once, after option resolution and interpreter discovery but
    before the destination lock is acquired. Receives
    :class:`HookContext` with ``options`` and ``reporter`` populated.

``pre_create``
    Fired immediately before the creator lays down the environment.
    ``HookContext.options`` and ``HookContext.reporter`` are populated.

``post_activators``
    Fired after every activation script has been written but before
    seeding. ``HookContext.data["scripts"]`` is the list of paths.

``post_seed``
    Fired after the seeder completes (or skips). ``HookContext.result``
    holds the final :class:`~tn_venv.session.SessionResult`.

``session_end``
    Fired last, just before :func:`run_session` returns. Hooks may mutate
    ``HookContext.result``; whatever they leave behind is what the caller
    receives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..report import Reporter
    from ..session import Options, SessionResult
    from .registry import HookRegistry


class HookName(str, Enum):
    """The lifecycle hooks emitted by ``run_session``.

    Subclassing ``str`` keeps the values JSON-/argparse-friendly while
    preserving the enum identity check.
    """

    SESSION_START = "session_start"
    PRE_CREATE = "pre_create"
    POST_ACTIVATORS = "post_activators"
    POST_SEED = "post_seed"
    SESSION_END = "session_end"
    HELP_EPILOG = "help_epilog"


#: Canonical entry-point group for third-party plugins. A ``pyproject.toml``
#: declares them as::
#:
#:     [project.entry-points."tn_venv.plugins"]
#:     my_plugin = "my_pkg.module:MyPlugin"
PLUGIN_ENTRY_POINT = "tn_venv.plugins"

#: Environment variable that lists extra plugins to load, comma separated.
#: Each entry is either a fully-qualified class (``pkg.module:Class``) or
#: a module whose top-level ``Plugin`` instances are picked up
#: automatically.
PLUGIN_ENV_VAR = "TN_VENV_PLUGINS"


@dataclass
class HookContext:
    """The single object passed to every hook callback.

    Hooks read fields they care about and may mutate :attr:`data` to share
    scratch values across hooks of the same run. :attr:`result` is only
    populated for hooks that fire after the session result has been
    constructed (``post_seed`` and ``session_end``).
    """

    options: "Options | None" = None
    reporter: "Reporter | None" = None
    result: "SessionResult | None" = None
    data: dict[str, Any] = field(default_factory=dict)


#: Signature every hook callback must satisfy.
HookFn = Callable[[HookContext], None]


class Plugin:
    """Base class for tn-venv plugins.

    Subclasses set :attr:`name` (used in error messages and the
    ``--list-plugins`` machinery if added later) and override
    :meth:`register`. The default implementation registers no hooks, so
    subclasses that want to participate in the lifecycle must call
    ``hooks.add(...)`` at least once.

    Example::

        class TimestampPlugin(Plugin):
            name = "timestamp"

            def register(self, hooks):
                hooks.add(HookName.SESSION_START, self._stamp)

            def _stamp(self, ctx):
                ctx.data["started_at"] = time.time()
    """

    #: Stable, human-readable identifier. Defaults to the class name.
    name: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.name:
            cls.name = cls.__name__

    def register(self, hooks: "HookRegistry") -> None:
        """Install hook callbacks on *hooks*.

        Subclasses override this to participate in the session lifecycle.
        The default implementation registers nothing, so a plugin with no
        override is effectively a no-op (and a valid way to attach config
        from the outside).
        """


__all__ = [
    "HookName",
    "HookContext",
    "HookFn",
    "Plugin",
    "PLUGIN_ENTRY_POINT",
    "PLUGIN_ENV_VAR",
]
