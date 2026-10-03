# Plugins

`tn-venv` ships with a small plugin system that lets you tap into the
creation pipeline at five well-defined points. Plugins can read and
modify the ``Options``, peek at the freshly built
``CreatorContext``, append activation
scripts, stamp metadata into `pyvenv.cfg`, install extra packages, log
information, or short-circuit parts of the process — all without
forking tn-venv.

The default install includes one built-in plugin
(``VersionStampPlugin``) that writes
`tn-venv-version = <version>` into `pyvenv.cfg` after the activation
scripts are generated.

## Quick start

The smallest possible plugin:

```python
# my_pkg/tnvenv_plugin.py
from tn_venv.plugins import HookName, Plugin


class TimestampPlugin(Plugin):
    name = "timestamp"

    def register(self, hooks):
        hooks.add(HookName.SESSION_START, self._stamp)

    def _stamp(self, ctx):
        ctx.data["started_at"] = time.time()
```

Register it in your `pyproject.toml`:

```toml
[project.entry-points."tn_venv.plugins"]
timestamp = "my_pkg.tnvenv_plugin:TimestampPlugin"
```

From now on, every `tn-venv` invocation will load your plugin
automatically.

## Hooks

The pipeline emits the following events, in order. Each callback
receives a single ``HookContext``.

| Hook | When | `ctx.data` keys populated by the pipeline |
|---|---|---|
| `SESSION_START` | after option resolution and interpreter discovery | `{}` |
| `PRE_CREATE` | immediately before `Creator.create()` | `{}` |
| `POST_ACTIVATORS` | after every activation script has been written | `cfg_path`, `env_dir`, `scripts` |
| `POST_SEED` | after the seeder finishes (or skips) | `cfg_path`, `env_dir`, `scripts`, `seed_result` |
| `SESSION_END` | last, just before `run_session` returns | all of the above plus `result` (a `SessionResult`) |

Hooks are *additive*: every registered callback runs. A listener that
raises is logged at warning level but does not abort the pipeline.

### `HookContext`

```python
@dataclass
class HookContext:
    options: Options | None          # the resolved Options
    reporter: Reporter | None        # for warn / debug / info
    result: SessionResult | None     # populated for SESSION_END
    data: dict[str, Any]             # per-run scratch space
```

`data` is shared across every hook of a single run, so plugins can pass
information forward (for example, an analysis plugin writes findings
under `data["findings"]` and a reporter plugin reads them in
`SESSION_END`).

## Discovery

The loader looks at three places, in order, deduplicating by class:

1. **Built-ins** — ``VersionStampPlugin`` is
   always loaded.
2. **Entry points** in the `tn_venv.plugins` group, declared by
   third-party packages.
3. **`TN_VENV_PLUGINS`** — an environment variable listing extra
   plugins, comma-separated. Each entry is one of:
   - `pkg.module:Class` — import `pkg.module` and instantiate `Class`.
   - `pkg.module` — import the module and look for either a
     `PLUGINS` iterable or any `Plugin` subclass defined there.

A plugin that fails to import or instantiate is logged at warning level
and skipped — your shell `tn-venv .venv` will not blow up because a
third-party plugin is broken.

### Declaring an entry point

In your package's `pyproject.toml`:

```toml
[project]
name = "my-pkg"
version = "0.1.0"

[project.entry-points."tn_venv.plugins"]
my_plugin = "my_pkg.tnvenv_plugin:MyPlugin"
```

`my_plugin` is the entry-point name (used for diagnostics only);
`my_pkg.tnvenv_plugin:MyPlugin` is the dotted path of the class to
instantiate.

### Using `TN_VENV_PLUGINS`

For ad-hoc testing you can point at any importable class:

```console
$ TN_VENV_PLUGINS="my_pkg.tnvenv_plugin:TimestampPlugin" tn-venv
```

The variable also accepts bare module names; in that case the loader
looks for a top-level `PLUGINS` iterable, then falls back to the first
`Plugin` subclass defined in the module.

## Writing a plugin

A plugin is a class subclassing ``Plugin`` with
a unique `name` and a `register` method:

```python
from tn_venv.plugins import HookContext, HookName, Plugin


class PyenvRcPlugin(Plugin):
    name = "pyenvrc"

    def register(self, hooks):
        hooks.add(HookName.POST_ACTIVATORS, self._write_pyenvrc, priority=50)

    def _write_pyenvrc(self, ctx):
        env_dir = ctx.data.get("env_dir")
        if env_dir is None:
            return
        (env_dir / ".python-version").write_text(ctx.options.python[0] + "\n")
```

### Priorities

`hooks.add(hook, fn, priority=N)` controls dispatch order. Higher
priorities run first; ties keep insertion order. Built-ins use
`DEFAULT_PRIORITY - 50` so your plugins run before them by default.
Override the priority when you need to be earlier (e.g. analyser
plugins) or later (e.g. final reporting).

### Returning values

Hooks **must return `None`**. Communicate through `ctx.data` or by
mutating `ctx.result` during `SESSION_END`. Returning a non-`None`
value is currently ignored and will become an error in a future
release.

### Reading options safely

`ctx.options` may be `None` for hooks fired outside a real session
(some test paths or programmatic invocations). Always check or use
`getattr(ctx, "options", None)`.

## Reference

- ``api`` — `Plugin`, `HookName`, `HookContext`,
  `PLUGIN_ENTRY_POINT`, `PLUGIN_ENV_VAR`.
- ``registry`` — `HookRegistry`, `DEFAULT_PRIORITY`.
- ``loader`` — `load_plugins`, `parse_plugin_spec`,
  `require_plugin`.
- ``builtin`` — `VersionStampPlugin`.
