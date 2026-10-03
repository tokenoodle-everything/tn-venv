"""Hook registry: priority-ordered listeners and a fault-tolerant emitter.

The registry is a small object passed to every :class:`Plugin.register`
implementation. Listeners are stored in *descending priority order* — the
default priority is ``100`` and the built-in plugin uses ``50`` so user
plugins run after it by default. Pass a lower number to run later, or a
higher number to run sooner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from ..report import Reporter, SILENT
from .api import HookContext, HookFn, HookName

if TYPE_CHECKING:
    from .builtin import Plugin

DEFAULT_PRIORITY = 100


@dataclass
class _Listener:
    fn: HookFn
    priority: int
    plugin_name: str  # for diagnostics


class HookRegistry:
    """Collects hook callbacks and dispatches events to them.

    Listeners for the same hook run in priority order (highest first);
    ties keep insertion order. A listener that raises is logged at warning
    level but does not abort the dispatch — other listeners still run.
    """

    def __init__(self, reporter: Reporter | None = None) -> None:
        self._reporter: Reporter = reporter if reporter is not None else SILENT
        self._listeners: dict[HookName, list[_Listener]] = {h: [] for h in HookName}

    # -- registration -------------------------------------------------------
    def add(
        self,
        hook: HookName | str,
        fn: HookFn | None = None,
        *,
        priority: int = DEFAULT_PRIORITY,
        plugin_name: str = "",
        _self: Plugin | None = None,
    ) -> Callable[[HookFn], HookFn] | None:
        """Register *fn* for *hook*.

        Can be used as ``hooks.add(HookName.SESSION_START, my_fn)`` or as
        a decorator: ``@hooks.add(HookName.SESSION_START)``. When used as
        a decorator, the priority defaults to :data:`DEFAULT_PRIORITY`.
        Returns the decorator's inner callable, or ``None`` when called
        directly with a function.
        """
        if isinstance(hook, str) and not isinstance(hook, HookName):
            try:
                hook = HookName(hook)
            except ValueError as exc:
                raise ValueError(
                    f"unknown hook {hook!r}; expected one of "
                    f"{[h.value for h in HookName]}"
                ) from exc
        if fn is not None:
            self._register(hook, fn, priority, plugin_name or _self_name(_self))
            return None

        def decorator(real_fn: HookFn) -> HookFn:
            self._register(hook, real_fn, priority, plugin_name or _self_name(_self))
            return real_fn

        return decorator

    def _register(
        self,
        hook: HookName,
        fn: HookFn,
        priority: int,
        plugin_name: str,
    ) -> None:
        listener = _Listener(fn=fn, priority=priority, plugin_name=plugin_name)
        bucket = self._listeners[hook]
        # Insert in priority order (highest first). Stable for equal priorities.
        for idx, existing in enumerate(bucket):
            if existing.priority < priority:
                bucket.insert(idx, listener)
                return
        bucket.append(listener)

    # -- introspection ------------------------------------------------------
    def listeners(self, hook: HookName | str) -> list[HookFn]:
        """Return the callables registered for *hook*, in dispatch order."""
        h = self._resolve(hook)
        return [l.fn for l in self._listeners[h]]

    def listener_count(self, hook: HookName | str) -> int:
        h = self._resolve(hook)
        return len(self._listeners[h])

    # -- emission -----------------------------------------------------------
    def emit(self, hook: HookName | str, ctx: HookContext | None = None) -> HookContext:
        """Call every listener registered for *hook* with *ctx*.

        Returns the (possibly mutated) context. Exceptions from one
        listener are caught and surfaced via the reporter at warning
        level; the remaining listeners still run.
        """
        h = self._resolve(hook)
        ctx = ctx if ctx is not None else HookContext()
        reporter = ctx.reporter or self._reporter
        for listener in self._listeners[h]:
            try:
                listener.fn(ctx)
            except Exception as exc:  # noqa: BLE001 - we really mean any error
                src = (
                    f"{listener.plugin_name}.{listener.fn.__qualname__}"
                    if listener.plugin_name
                    else listener.fn.__qualname__
                )
                reporter.warn(f"plugin hook {h.value!r} raised in {src}: {exc}")
        return ctx

    @staticmethod
    def _resolve(hook: HookName | str) -> HookName:
        if isinstance(hook, HookName):
            return hook
        try:
            return HookName(hook)
        except ValueError as exc:
            raise ValueError(
                f"unknown hook {hook!r}; expected one of {[h.value for h in HookName]}"
            ) from exc


def _self_name(plugin: object | None) -> str:
    if plugin is None:
        return ""
    name = getattr(plugin, "name", "") or ""
    return name or type(plugin).__name__


__all__ = ["HookRegistry", "DEFAULT_PRIORITY"]
