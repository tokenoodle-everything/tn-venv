# Authoring

This page is the deep reference for the objects a plugin author
touches: `Plugin`, `HookRegistry`, `HookContext`, `PluginSource`,
and the dataclasses that wrap them.

## `Plugin`

```python
class Plugin:
    """Base class for tn-venv plugins."""

    #: Stable, human-readable identifier. Defaults to the class name
    #: via __init_subclass__, but you should set this explicitly.
    name: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.name:
            cls.name = cls.__name__

    def register(self, hooks: HookRegistry) -> None:
        """Install hook callbacks on *hooks*.

        Subclasses override this to participate in the session
        lifecycle. The default implementation registers nothing, so
        a plugin with no override is effectively a no-op.
        """
```

### Why override `register()` instead of putting logic in `__init__`?

`__init__` runs every time the loader instantiates your class — for
entry points, once per `load_plugins()` call. The hook callbacks
would be added to the registry every time the plugin is
constructed, which double-registers on a reload. Putting the work
in `register()` keeps construction cheap and registration explicit.

### Empty `name` ⇒ private base class

If you write `class _Base(Plugin): pass`, the auto-assigned `name`
is `_Base` (the class name). The loader skips empty-named bases —
see {doc}`discovery` for the full rule. Use empty `name` to mark
abstract bases; use a real string for concrete ones.

### What 1.x guarantees about `Plugin`

- `Plugin` itself never gains required arguments.
- `name` keeps its semantics. Don't add side effects to
  `__init_subclass__` other than filling in `name`.
- New `HookName` enum members may be added in minor versions. They
  are non-breaking because plugins opt in by name.

What `Plugin` **does not** guarantee:

- That subclasses can be instantiated multiple times safely. The
  loader instantiates each class **once per `load_plugins()` call**.
  If your `__init__` has side effects (e.g. opening a file), make
  them idempotent.

## `HookContext`

A dataclass with four fields. See {doc}`hooks` for the full
discussion of when each field is populated. The fields:

| Field | Type | Populated when |
|---|---|---|
| `options` | `Options \| None` | every lifecycle hook; `None` outside a real session |
| `reporter` | `Reporter \| None` | every lifecycle hook; falls back to the registry's reporter if `None` |
| `result` | `SessionResult \| None` | only `SESSION_END` |
| `data` | `dict[str, Any]` | always; populated incrementally by the pipeline and plugins |

The `data` dict is the only mutable field. Use it for cross-hook
state within a single run — never store anything in
`Plugin.__init__` and expect it to survive across runs.

## `HookRegistry`

The dispatcher. Plugins get a `HookRegistry` reference via
`register(hooks)`. The registry is **fresh per `load_plugins()` call**
— don't cache it in a module-level variable.

### Constructor

```python
HookRegistry(reporter: Reporter | None = None) -> None
```

If `reporter` is omitted, `Reporter(verbosity=-1)` is used (silent).

### `add()` — register a listener

Two forms:

```python
# Direct form — pass the callable explicitly:
hooks.add(
    HookName.SESSION_START,
    my_func,
    priority=100,             # optional, default DEFAULT_PRIORITY (100)
    plugin_name="my_plugin",  # optional, shown in warnings / introspection
)

# Decorator form — used as @hooks.add(hook, ...):
@hooks.add(HookName.SESSION_START, plugin_name="my_plugin")
def my_listener(ctx):
    ...
```

The decorator form is equivalent. Both register at the time
`add()` is *called* (or the decorator is applied); the registry
saves the callable and `plugin_name` for diagnostics.

**Decorator trap**: the decorator factory's return value (the inner
function) is what `plugins[0]` stores. If you decorate a free
function and lose the return value, your listener is silently lost.
This is rarely hit in practice but worth noting.

### `emit()` — dispatch

```python
registry.emit(HookName.SESSION_START, ctx) -> HookContext
```

Returns the (possibly mutated) `ctx`. Exceptions from listeners
are caught and logged at warning level; other listeners on the same
hook still run.

### `collect_help_epilog()` — for `HELP_EPILOG` listeners

```python
text: str = registry.collect_help_epilog()
```

Concatenates the return values of every `HELP_EPILOG` listener with
blank-line separators. `None` and `""` returns are skipped.

### Introspection

For most code you don't need to introspect the registry. But
`tn-venv --list-plugins` does, so the registry exposes:

| Member | Meaning |
|---|---|
| `listeners(hook)` | The callables registered for `hook`, in dispatch order |
| `listener_count(hook)` | The number of callables for `hook` |
| `_listeners` | The internal `dict[HookName, list[_Listener]]` |
| `_owners` | `dict[id(fn), Plugin]` populated by `_register_with_owner` so introspection can find the plugin that registered each callable |
| `_hookless_plugins` | `list[Plugin]` of plugins whose `register()` ran without calling `hooks.add()` (CLI shims, subcommand installers, …) |

These are all part of the contract that `tn-venv --list-plugins`
relies on. Reading them is fine; mutating them externally will
silently desync the registry.

## `PluginSource`

```python
@dataclass(frozen=True)
class PluginSource:
    """Provenance for a loaded Plugin."""

    kind: str   # "built-in" | "entry-point" | "env"
    spec: str   # e.g. "VersionStampPlugin", or
                # "hooks=tn_venv_gui.plugin:GuiHookPlugin", or "TN_VENV_PLUGINS"
```

Every successfully-loaded `Plugin` instance is annotated with a
private `_tn_venv_source` attribute (a `PluginSource`) by
`load_plugins`. The attribute is private (leading underscore) but
the dataclass itself is part of the public API — callers can read
it like:

```python
registry = load_plugins(reporter=SILENT)
for plugin in registry._owners.values():
    src = getattr(plugin, "_tn_venv_source", None)
    if src is not None:
        print(f"{plugin.name} from {src.kind}: {src.spec}")
```

Plugins should treat `_tn_venv_source` as **read-only**. The
leading underscore signals "set by the loader, not by the plugin
author".

If your plugin uses `__slots__` and disallows new attributes, the
loader will catch the resulting `AttributeError` and continue —
your plugin just won't show up in the `source:` column of
`tn-venv --list-plugins`.

## Adding a new hook

Hooks live on the `HookName` enum:

```python
# tn_venv/plugins/api.py
class HookName(str, Enum):
    SESSION_START = "session_start"
    PRE_CREATE = "pre_create"
    POST_ACTIVATORS = "post_activators"
    POST_SEED = "post_seed"
    SESSION_END = "session_end"
    HELP_EPILOG = "help_epilog"
```

**Don't** add a new hook to `tn_venv.plugins` and ship it from a
third-party plugin — tn-venv owns the hook set. If you need a hook
that doesn't exist, file an issue describing the timing and payload
you need.

What you **can** do as a third-party plugin:

- Subscribe to any existing hook.
- Mutate `ctx.data` with your own keys (the pipeline's keys are
  reserved but yours are not).
- Add a new attribute to a `HookContext` subclass if you pass
  your own subclass (advanced; not recommended).

## `require_plugin` — looking up a built-in

```python
from tn_venv.plugins import require_plugin

Vs = require_plugin("version_stamp")   # → VersionStampPlugin
# or raises ConfigError if no built-in matches
```

`require_plugin` is the mirror image of `getattr` for the built-in
plugin registry. It's exposed so third-party code can integrate with
a specific built-in without importing its module directly.

## Where to read the source

The whole `tn_venv.plugins` package is small enough to read in one
sitting:

```text
tn_venv/plugins/
├── __init__.py      ← public re-exports
├── api.py           ← HookName, HookContext, HookFn, Plugin, PluginSource
├── registry.py      ← HookRegistry, _Listener, DEFAULT_PRIORITY
├── loader.py        ← load_plugins, _iter_entry_points, _instantiate,
│                     _from_entry_point, _from_module_attr,
│                     _from_env, _resolve_target, _tag_source,
│                     _register_with_owner, PluginSource
└── builtin.py       ← VersionStampPlugin
```

`loader.py` is the file you'll want to read if you're debugging
discovery or wondering how the `seen` set works. The other three
files are mostly stable interfaces.