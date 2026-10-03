"""Discover and instantiate plugins.

Discovery sources (later sources override earlier ones on collision):

1. The built-in :class:`~tn_venv.plugins.builtin.VersionStampPlugin`,
   which is always loaded.
2. Python *entry points* in the
   :data:`tn_venv.plugins.api.PLUGIN_ENTRY_POINT` group, advertised by
   third-party packages in their ``pyproject.toml``.
3. The :data:`~tn_venv.plugins.api.PLUGIN_ENV_VAR` environment variable,
   a comma-separated list of either ``package.module:Class`` references
   or bare module names (in which case the module's ``PLUGINS`` global
   is consulted, falling back to instantiating the first ``Plugin``
   subclass found).

Failure to import or instantiate a plugin is logged as a warning — the
core pipeline must keep working when a user-supplied plugin is broken.
"""

from __future__ import annotations

import importlib
import os
from importlib import metadata
from typing import Iterable

from ..errors import ConfigError
from ..report import Reporter, SILENT
from .api import PLUGIN_ENTRY_POINT, PLUGIN_ENV_VAR, Plugin
from .builtin import VersionStampPlugin
from .registry import HookRegistry

_BUILTINS: tuple[type[Plugin], ...] = (VersionStampPlugin,)


def _iter_entry_points() -> Iterable[metadata.EntryPoint]:
    try:
        eps = metadata.entry_points()
    except Exception:  # pragma: no cover - very defensive
        return ()
    try:
        return eps.select(group=PLUGIN_ENTRY_POINT)  # type: ignore[attr-defined]
    except AttributeError:  # pragma: no cover - older API
        group = eps.get(PLUGIN_ENTRY_POINT, [])  # type: ignore[attr-defined]
        return iter(group)


def _instantiate(
    plugin_cls: type[Plugin],
    *,
    reporter: Reporter,
    origin: str,
) -> Plugin | None:
    if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, Plugin):
        reporter.warn(
            f"ignoring {origin}: {plugin_cls!r} is not a Plugin subclass"
        )
        return None
    try:
        return plugin_cls()
    except Exception as exc:  # noqa: BLE001
        reporter.warn(
            f"failed to instantiate plugin {origin} ({plugin_cls!r}): {exc}"
        )
        return None


def _from_entry_point(
    ep: metadata.EntryPoint,
    *,
    reporter: Reporter,
    seen: set[type[Plugin]],
) -> Plugin | None:
    origin = f"entry point {ep.name!r} ({ep.value})"
    try:
        loaded = ep.load()
    except Exception as exc:  # noqa: BLE001
        reporter.warn(f"failed to load plugin {origin}: {exc}")
        return None
    if isinstance(loaded, Plugin):
        if type(loaded) in seen:
            return None
        seen.add(type(loaded))
        return loaded
    if isinstance(loaded, type) and issubclass(loaded, Plugin):
        if loaded in seen:
            return None
        seen.add(loaded)
        return _instantiate(loaded, reporter=reporter, origin=origin)
    if hasattr(loaded, "PLUGINS"):
        return _from_module_attr(
            loaded, attr="PLUGINS", reporter=reporter, seen=seen
        )
    reporter.warn(
        f"ignoring {origin}: did not resolve to a Plugin subclass, "
        "instance, or module with PLUGINS"
    )
    return None


def _from_module_attr(
    module: object,
    *,
    attr: str,
    reporter: Reporter,
    seen: set[type[Plugin]],
) -> Plugin | None:
    origin = f"module {module.__name__}.{attr}"  # type: ignore[attr-defined]
    candidates = getattr(module, attr, None)
    if candidates is None:
        candidates = [
            obj
            for obj in vars(module).values()
            if isinstance(obj, type)
            and issubclass(obj, Plugin)
            and obj is not Plugin
        ]
    if not candidates:
        reporter.warn(f"no plugins found in {origin}")
        return None
    out: Plugin | None = None
    for cls in candidates:
        if cls in seen:
            continue
        seen.add(cls)
        instance = _instantiate(cls, reporter=reporter, origin=origin)
        if instance is not None and out is None:
            out = instance
    return out


def _import_string(dotted: str, reporter: Reporter) -> object | None:
    """Resolve ``pkg.module`` or ``pkg.module:Attr`` to its target object."""
    if ":" in dotted:
        mod_part, attr = dotted.split(":", 1)
        attr = attr.strip()
    else:
        mod_part, attr = dotted, ""
    mod_part = mod_part.strip()
    if not mod_part:
        reporter.warn("ignoring empty plugin spec in TN_VENV_PLUGINS")
        return None
    try:
        module = importlib.import_module(mod_part)
    except Exception as exc:  # noqa: BLE001
        reporter.warn(f"failed to import plugin module {mod_part!r}: {exc}")
        return None
    if not attr:
        return module
    try:
        return getattr(module, attr)
    except AttributeError as exc:
        reporter.warn(f"plugin target {dotted!r} not found: {exc}")
        return None


def _from_env(
    env_value: str,
    *,
    reporter: Reporter,
    seen: set[type[Plugin]],
) -> list[Plugin]:
    out: list[Plugin] = []
    for raw in env_value.split(","):
        spec = raw.strip()
        if not spec:
            continue
        target = _import_string(spec, reporter=reporter)
        if target is None:
            continue
        plugin = _resolve_target(target, spec=spec, reporter=reporter, seen=seen)
        if plugin is not None:
            out.append(plugin)
    return out


def _resolve_target(
    target: object,
    *,
    spec: str,
    reporter: Reporter,
    seen: set[type[Plugin]],
) -> Plugin | None:
    if isinstance(target, Plugin):
        if type(target) in seen:
            return None
        seen.add(type(target))
        return target
    if isinstance(target, type) and issubclass(target, Plugin):
        if target in seen:
            return None
        seen.add(target)
        return _instantiate(target, reporter=reporter, origin=f"spec {spec!r}")
    return _from_module_attr(target, attr="PLUGINS", reporter=reporter, seen=seen)


def load_plugins(
    reporter: Reporter | None = None,
    *,
    env: dict[str, str] | None = None,
) -> HookRegistry:
    """Build a populated :class:`HookRegistry`.

    Always loads the built-in :class:`VersionStampPlugin`, then merges in
    entry points and any plugins listed in
    :data:`~tn_venv.plugins.api.PLUGIN_ENV_VAR`. Duplicate classes (same
    ``Plugin`` subclass appearing via multiple sources) are loaded only
    once.
    """
    reporter = reporter if reporter is not None else SILENT
    seen: set[type[Plugin]] = set()
    plugins: list[Plugin] = []

    for cls in _BUILTINS:
        if cls in seen:
            continue
        seen.add(cls)
        instance = _instantiate(
            cls, reporter=reporter, origin=f"built-in {cls.__name__}"
        )
        if instance is not None:
            plugins.append(instance)

    for ep in _iter_entry_points():
        plugin = _from_entry_point(ep, reporter=reporter, seen=seen)
        if plugin is not None:
            plugins.append(plugin)

    environ = env if env is not None else os.environ
    env_value = environ.get(PLUGIN_ENV_VAR, "")
    if env_value:
        plugins.extend(_from_env(env_value, reporter=reporter, seen=seen))

    registry = HookRegistry(reporter=reporter)
    for plugin in plugins:
        try:
            plugin.register(registry)
        except Exception as exc:  # noqa: BLE001
            reporter.warn(
                f"plugin {getattr(plugin, 'name', type(plugin).__name__)!r} "
                f"failed to register: {exc}"
            )
    reporter.debug(f"loaded {len(plugins)} plugin(s)")
    return registry


__all__ = ["load_plugins", "parse_plugin_spec", "require_plugin"]


def parse_plugin_spec(value: str) -> list[str]:
    """Split a ``TN_VENV_PLUGINS``-style value into its deduplicated parts.

    Useful for tests and for callers that want to feed plugin specs
    through their own validation pipeline. No import is attempted; pass
    the list to :func:`load_plugins` (or use it directly) for that.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in value.split(","):
        spec = raw.strip()
        if not spec or spec in seen:
            continue
        seen.add(spec)
        out.append(spec)
    return out


def require_plugin(name: str) -> type[Plugin]:
    """Look up a built-in plugin class by :attr:`Plugin.name`.

    Raises :class:`ConfigError` when no built-in matches.
    """
    for cls in _BUILTINS:
        if cls.name == name:
            return cls
    raise ConfigError(f"no built-in plugin named {name!r}")

