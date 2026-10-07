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
from dataclasses import dataclass
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
        reporter.warn(f"ignoring {origin}: {plugin_cls!r} is not a Plugin subclass")
        return None
    try:
        return plugin_cls()
    except Exception as exc:  # noqa: BLE001
        reporter.warn(f"failed to instantiate plugin {origin} ({plugin_cls!r}): {exc}")
        return None


def _from_entry_point(
    ep: metadata.EntryPoint,
    *,
    reporter: Reporter,
    seen: set[type[Plugin]],
) -> list[Plugin]:
    """Resolve one entry point to zero, one, or many plugin instances."""
    origin = f"entry point {ep.name!r} ({ep.value})"
    try:
        loaded = ep.load()
    except Exception as exc:  # noqa: BLE001
        reporter.warn(f"failed to load plugin {origin}: {exc}")
        return []
    if isinstance(loaded, Plugin):
        if type(loaded) in seen:
            return []
        seen.add(type(loaded))
        return [loaded]
    if isinstance(loaded, type) and issubclass(loaded, Plugin):
        if loaded in seen:
            return []
        seen.add(loaded)
        instance = _instantiate(loaded, reporter=reporter, origin=origin)
        return [instance] if instance is not None else []
    if hasattr(loaded, "PLUGINS"):
        return _from_module_attr(loaded, attr="PLUGINS", reporter=reporter, seen=seen)
    reporter.warn(
        f"ignoring {origin}: did not resolve to a Plugin subclass, "
        "instance, or module with PLUGINS"
    )
    return []


def _from_module_attr(
    module: object,
    *,
    attr: str,
    reporter: Reporter,
    seen: set[type[Plugin]],
) -> list[Plugin]:
    """Instantiate every plugin class exposed by *module* (one or many).

    Returns a list (possibly empty) of successfully constructed plugin
    instances. The candidates are read, in order, from:

    1. ``module.PLUGINS`` — an iterable of plugin classes, or
    2. The module's own namespace, scanning for non-base
       :class:`~tn_venv.plugins.api.Plugin` subclasses.

    Two filters are applied during the scan:

    - The class itself (``Plugin``) is always skipped.
    - Classes whose ``name`` is empty — typically abstract or helper
      bases that inherit from ``Plugin`` but are not meant to be
      instantiated — are skipped. A class with an empty name
      indicates "I haven't been given a name yet", which in this
      codebase only happens for intermediate bases.

    Each candidate is added to *seen* exactly once; duplicates inside
    the same module are silently ignored, matching the cross-source
    dedup contract.
    """
    origin = f"module {module.__name__}.{attr}"  # type: ignore[attr-defined]
    candidates = getattr(module, attr, None)
    if candidates is None:
        candidates = _scan_module_for_plugins(module)
    if not candidates:
        reporter.warn(f"no plugins found in {origin}")
        return []
    out: list[Plugin] = []
    for cls in candidates:
        if not isinstance(cls, type) or not issubclass(cls, Plugin):
            reporter.warn(f"ignoring {origin}: {cls!r} is not a Plugin subclass")
            continue
        # Skip abstract / helper bases. A Plugin subclass with empty
        # ``name`` is treated as not-a-concrete-plugin.
        if not getattr(cls, "name", ""):
            continue
        if cls in seen:
            continue
        seen.add(cls)
        instance = _instantiate(cls, reporter=reporter, origin=origin)
        if instance is not None:
            out.append(instance)
    return out


def _scan_module_for_plugins(module: object) -> list[type[Plugin]]:
    """Find every concrete ``Plugin`` subclass defined directly in *module*.

    Returns them in the module's ``vars()`` order. Intermediate bases
    (classes with an empty ``name``) are filtered out so the concrete
    plugin at the bottom of the MRO is what the loader actually picks.
    """
    out: list[type[Plugin]] = []
    for obj in vars(module).values():
        if not isinstance(obj, type) or not issubclass(obj, Plugin):
            continue
        if obj is Plugin:
            continue
        # An empty ``name`` is the convention we use for an intermediate
        # base class — e.g. ``class _Base(Plugin): ...`` followed by
        # ``class Concrete(_Base): name = "concrete"``. Skipping the
        # base avoids the "first class wins" trap and lets the
        # concrete plugin be loaded.
        if not getattr(obj, "name", ""):
            continue
        out.append(obj)
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
        out.extend(_resolve_target(target, spec=spec, reporter=reporter, seen=seen))
    return out


def _resolve_target(
    target: object,
    *,
    spec: str,
    reporter: Reporter,
    seen: set[type[Plugin]],
) -> list[Plugin]:
    """Turn *target* (one of: Plugin instance, Plugin subclass, module)
    into a list of zero, one, or many plugin instances.
    """
    if isinstance(target, Plugin):
        if type(target) in seen:
            return []
        seen.add(type(target))
        return [target]
    if isinstance(target, type) and issubclass(target, Plugin):
        if target in seen:
            return []
        seen.add(target)
        instance = _instantiate(target, reporter=reporter, origin=f"spec {spec!r}")
        return [instance] if instance is not None else []
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

    Every successfully loaded :class:`Plugin` instance is annotated with
    a private ``_tn_venv_source`` attribute (a :class:`PluginSource`)
    describing where it came from. The CLI's ``--list-plugins`` flag
    reads these back to render a human-friendly summary; the attribute
    is private and not part of the public plugin contract.
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
            _tag_source(instance, PluginSource(kind="built-in", spec=cls.__name__))
            plugins.append(instance)

    for ep in _iter_entry_points():
        loaded = _from_entry_point(ep, reporter=reporter, seen=seen)
        for instance in loaded:
            _tag_source(
                instance,
                PluginSource(kind="entry-point", spec=f"{ep.name}={ep.value}"),
            )
        plugins.extend(loaded)

    environ = env if env is not None else os.environ
    env_value = environ.get(PLUGIN_ENV_VAR, "")
    if env_value:
        loaded = _from_env(env_value, reporter=reporter, seen=seen)
        for instance in loaded:
            _tag_source(instance, PluginSource(kind="env", spec=PLUGIN_ENV_VAR))
        plugins.extend(loaded)

    registry = HookRegistry(reporter=reporter)
    for plugin in plugins:
        try:
            # Wrap the registry so every listener registered by this
            # plugin is tagged with its owner. We do it via a thin proxy
            # rather than monkey-patching the registry, so the public
            # ``hooks.add`` signature stays unchanged.
            _register_with_owner(registry, plugin)
        except Exception as exc:  # noqa: BLE001
            reporter.warn(
                f"plugin {getattr(plugin, 'name', type(plugin).__name__)!r} "
                f"failed to register: {exc}"
            )
    reporter.debug(f"loaded {len(plugins)} plugin(s)")
    return registry


def _register_with_owner(registry: HookRegistry, plugin: Plugin) -> None:
    """Bind *plugin* as the owner of every listener it adds during this call.

    Implementation: temporarily swap ``registry.add`` for a wrapper that
    records ``(id(fn), plugin)`` in ``registry._owners``. The wrapper is
    restored in a ``finally`` so a plugin that raises mid-``register``
    cannot leave the registry in a broken state.

    Plugins that call ``register(hooks)`` but never add a hook (e.g.
    ``GuiSubcommandPlugin`` in tn-venv-gui, which installs a CLI
    subcommand as a side effect) are still recorded under the
    sentinel key ``0`` so the introspection helpers (``tn-venv
    --list-plugins``) can show them.
    """
    original_add = registry.add
    pending: dict[int, object] = {}

    def _owning_add(hook, fn=None, *, priority=100, plugin_name="", _self=None):
        # Direct form: pass through to original_add and remember the
        # callable that was just registered.
        if fn is not None:
            original_add(
                hook, fn, priority=priority, plugin_name=plugin_name, _self=_self
            )
            pending[id(fn)] = plugin
            return None
        # Decorator form: ask the original add for its decorator, then
        # wrap it so the wrapped real_fn gets owner-tagged too. We
        # MUST defer to original_add's actual registration (which
        # handles priority insertion and plugin_name resolution);
        # re-implementing it here would silently desync.
        original_decorator = original_add(
            hook, None, priority=priority, plugin_name=plugin_name, _self=_self
        )

        def _wrapping_decorator(real_fn):
            decorated = original_decorator(real_fn)  # type: ignore # pyrefly: ignore [not-callable]
            pending[id(decorated)] = plugin
            return decorated

        return _wrapping_decorator

    registry.add = _owning_add  # type: ignore[assignment]
    try:
        plugin.register(registry)
    finally:
        registry.add = original_add  # type: ignore[assignment]
    for fn_id, owner in pending.items():
        registry._owners[fn_id] = owner
    if not pending:
        # Plugin ran but never added a hook — still record it so the
        # listing machinery can surface side-effect-only plugins
        # (e.g. CLI subcommand shims). The registry keeps these in a
        # separate list to avoid colliding with id-based keys.
        registry._hookless_plugins.append(plugin)


@dataclass(frozen=True)
class PluginSource:
    """Provenance for a loaded :class:`Plugin`.

    Attached to each plugin instance as ``_tn_venv_source`` by
    :func:`load_plugins`. ``kind`` is one of ``"built-in"``,
    ``"entry-point"``, or ``"env"``; ``spec`` is the human-readable
    description of where the loader found it (e.g. ``"hooks=
    tn_venv_gui.plugin:GuiHookPlugin"`` for an entry point).
    """

    kind: str
    spec: str


def _tag_source(plugin: Plugin, source: PluginSource) -> None:
    """Stash *source* on *plugin* as a private attribute.

    Failure to set an attribute on a hostile plugin (e.g. one with a
    ``__slots__`` that disallows new attrs) is silently swallowed —
    the listing machinery degrades to "unknown source" rather than
    breaking the pipeline.
    """
    try:
        plugin._tn_venv_source = source  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


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
