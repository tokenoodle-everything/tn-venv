# Reference

One-screen API table for everything in `tn_venv.plugins`. For
narrative documentation, see the rest of this directory; for the
implementation, see {doc}`../development/extending`.

## Imports

```python
from tn_venv.plugins import (
    # Base classes
    Plugin,
    HookContext,
    HookRegistry,
    # Hooks
    HookName,
    # Functions
    load_plugins,
    parse_plugin_spec,
    require_plugin,
    # Provenance
    PluginSource,
    # Constants
    PLUGIN_ENTRY_POINT,    # "tn_venv.plugins"
    PLUGIN_ENV_VAR,        # "TN_VENV_PLUGINS"
    DEFAULT_PRIORITY,      # 100
    # Built-ins
    VersionStampPlugin,
)
```

The same names are re-exported from `tn_venv`:

```python
from tn_venv import (
    Plugin,
    HookContext,
    HookName,
    VersionStampPlugin,
    load_plugins,
)
```

## `Plugin`

| Member | Signature | Notes |
|---|---|---|
| `name` | `str = ""` | Stable identifier. Auto-assigned from class name on subclass if empty. |
| `__init_subclass__(cls, **kwargs)` | classmethod | Auto-fills `cls.name` if empty. |
| `register(self, hooks)` | `(HookRegistry) -> None` | Override to install listeners. Default is a no-op. |

## `HookContext`

| Field | Type | When populated |
|---|---|---|
| `options` | `Options \| None` | every lifecycle hook |
| `reporter` | `Reporter \| None` | every lifecycle hook |
| `result` | `SessionResult \| None` | only `SESSION_END` |
| `data` | `dict[str, Any]` | always; populated by the pipeline |

## `HookName`

| Member | Value | Fired by |
|---|---|---|
| `SESSION_START` | `"session_start"` | `run_session`, after discovery, before lock |
| `PRE_CREATE` | `"pre_create"` | `run_session`, immediately before `Creator.create()` |
| `POST_ACTIVATORS` | `"post_activators"` | `run_session`, after activators, before seed |
| `POST_SEED` | `"post_seed"` | `run_session`, after seed |
| `SESSION_END` | `"session_end"` | `run_session`, just before return |
| `HELP_EPILOG` | `"help_epilog"` | CLI `--help` rendering |

## `HookRegistry`

| Method | Signature | Notes |
|---|---|---|
| `__init__(reporter=None)` | | `reporter` defaults to silent. |
| `add(hook, fn=None, *, priority=DEFAULT_PRIORITY, plugin_name="")` | returns decorator or `None` | Two forms: `add(hook, fn, ...)` or `@add(hook, ...)`. |
| `emit(hook, ctx=None)` | returns `HookContext` | Calls every listener in priority order. |
| `collect_help_epilog()` | returns `str` | Concatenates every `HELP_EPILOG` listener's return. |
| `listeners(hook)` | returns `list[HookFn]` | Read-only introspection. |
| `listener_count(hook)` | returns `int` | Read-only introspection. |

Internal members used by introspection (`tn-venv --list-plugins`):

| Member | Type |
|---|---|
| `_listeners` | `dict[HookName, list[_Listener]]` |
| `_owners` | `dict[id(fn), Plugin]` |
| `_hookless_plugins` | `list[Plugin]` |

## `PluginSource`

| Field | Type | Example |
|---|---|---|
| `kind` | `str` | `"built-in"`, `"entry-point"`, `"env"` |
| `spec` | `str` | `"VersionStampPlugin"`, `"hooks=tn_venv_gui.plugin:GuiHookPlugin"`, `"TN_VENV_PLUGINS"` |

`PluginSource` instances are exposed as the private
`_tn_venv_source` attribute on every loaded `Plugin`.

## `load_plugins`

```python
def load_plugins(
    reporter: Reporter | None = None,
    *,
    env: dict[str, str] | None = None,
) -> HookRegistry: ...
```

- `reporter`: where warnings go. Defaults to `SILENT`.
- `env`: an explicit env-var override. Defaults to `os.environ`.
  Pass `env={}` to disable `TN_VENV_PLUGINS` for tests.

Returns a fresh `HookRegistry` populated with every successfully-loaded
plugin's hooks. See {doc}`discovery` for the full semantics.

## `parse_plugin_spec`

```python
def parse_plugin_spec(value: str) -> list[str]: ...
```

Splits a `TN_VENV_PLUGINS`-style value into a deduplicated list of
spec strings. Empty entries are dropped. No import is performed —
this is a pure string utility for tools and tests.

```python
parse_plugin_spec("a:A, b:B ,a,c")   # → ['a:A', 'b:B', 'c']
```

## `require_plugin`

```python
def require_plugin(name: str) -> type[Plugin]: ...
```

Looks up a built-in plugin class by `Plugin.name`. Raises
`ConfigError` when no built-in matches. Useful for third-party
plugins that want to integrate with a specific built-in (e.g.
decorate `VersionStampPlugin`'s output) without importing its
module directly.

## Constants

| Constant | Value | Where used |
|---|---|---|
| `PLUGIN_ENTRY_POINT` | `"tn_venv.plugins"` | the entry-point group declared in `pyproject.toml` |
| `PLUGIN_ENV_VAR` | `"TN_VENV_PLUGINS"` | the env var read by `load_plugins()` |
| `DEFAULT_PRIORITY` | `100` | the default `priority` argument for `hooks.add()` |

## Built-ins

`VersionStampPlugin` — registered as the `version_stamp` built-in.
Appends `tn-venv-version = <version>` to `pyvenv.cfg` after the
activation scripts have been generated. Doubles as the worked
example for new plugins — `tn_venv/plugins/builtin.py` is the
canonical short example of the public API.

## Errors

Plugins raise their own errors (typically `ConfigError` from
`tn_venv.errors`) and the loader logs them at warning level. The
loader itself does not introduce new error types; the only
`ConfigError` it produces directly is from `require_plugin`.