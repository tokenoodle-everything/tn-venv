# Discovery

When `tn-venv` loads plugins, it consults three sources in order and
deduplicates by class. This page explains what each source does, the
deduplication rules, and what happens when a source fails.

## The three sources

```text
load_plugins(reporter=None, *, env=None)
    │
    ├─ built-ins              ── always loaded first
    │
    ├─ entry points           ── group="tn_venv.plugins"
    │                          loaded from every installed distribution
    │
    └─ TN_VENV_PLUGINS        ── comma-separated env-var override
```

### 1. Built-ins

The loader always instantiates `tn_venv.plugins.builtin.VersionStampPlugin`
first. Built-ins are part of the tn-venv distribution itself and ship
their own entry point free. To inspect the built-in list at runtime:

```python
from tn_venv.plugins import require_plugin
cls = require_plugin("version_stamp")   # returns VersionStampPlugin
```

`require_plugin(name)` raises `ConfigError` when no built-in matches
— it's the equivalent of `getattr` for the built-in registry.

### 2. Entry points (third-party packages)

Every installed Python distribution can advertise plugins via the
`tn_venv.plugins` entry-point group:

```toml
[project.entry-points.tn_venv.plugins]
my_plugin = "my_pkg.module:MyPlugin"
```

The loader uses `importlib.metadata.entry_points()` to enumerate
distributions. For each `tn_venv.plugins` entry point, it:

1. Calls `ep.load()` to import the target module / class.
2. If the loaded object is a `Plugin` subclass → instantiate it.
3. If the loaded object is a `Plugin` instance → use it directly.
4. If the loaded object is a module with a `PLUGINS` iterable →
   iterate it and instantiate each member.
5. If the loaded object is a module with `Plugin` subclasses but
   no `PLUGINS` → instantiate the concrete ones (those with a
   non-empty `name`; empty-named bases are skipped).

The entry-point name (the left-hand side) is purely diagnostic — it
shows up in `tn-venv --list-plugins` as `entry-point: NAME=SPEC`.

### 3. `TN_VENV_PLUGINS` (ad-hoc override)

The `TN_VENV_PLUGINS` environment variable lets you load a plugin
**without** installing it. Useful for development, debugging, and
running a one-off Python file as a plugin.

The variable takes a comma-separated list. Each item is either:

| Form | What happens |
|---|---|
| `pkg.module:Class` | import `pkg.module`, instantiate `Class` |
| `pkg.module` | import `pkg.module`; instantiate whatever the module's `PLUGINS` iterable contains, or the first concrete `Plugin` subclass found in the module |
| (empty) | ignored |

Empty entries are dropped. Duplicates are removed. Example:

```bash
TN_VENV_PLUGINS='my_pkg:DemoPlugin,/path/to/local.py:LocalPlugin' tn-venv .venv
```

Parsing helpers:

```python
from tn_venv.plugins import parse_plugin_spec
parse_plugin_spec("a:A, b:B ,a,c")   # → ['a:A', 'b:B', 'c']
```

`parse_plugin_spec` is the same split the loader uses internally —
it's exposed for tests and tooling.

## Order and deduplication

The three sources are merged in the order above, and the resulting
list is deduplicated by **plugin class**:

```text
load_plugins() →
    [VersionStampPlugin,                          # from built-ins
     GuiHookPlugin, GuiSubcommandPlugin,           # from entry points
     DemoPlugin]                                # from TN_VENV_PLUGINS
```

If the same `Plugin` subclass appears via two sources (e.g. an
entry point plus `TN_VENV_PLUGINS`), only the **first** occurrence
wins. The loader sets `seen.add(cls)` after the first successful
instantiation and skips the rest.

`Plugin` **instances** are deduplicated by their **type** — two
instances of `DemoPlugin` will not appear, but `DemoPlugin()` and
`DemoPlugin()` (different instances, same class) won't both be
loaded.

The dedup is per-`load_plugins()` call, not per-process. Two calls
return fresh instances.

## What `load_plugins` returns

A `HookRegistry` populated with every successfully-loaded plugin's
hooks. Plugins whose `register()` ran without calling `hooks.add`
are still tracked in `HookRegistry._hookless_plugins` so
`tn-venv --list-plugins` can show them. See {doc}`hooks` and
{doc}`cli-integration`.

## Failure isolation

Each source is fault-isolated. The loader catches `Exception` (broad
on purpose — third-party code is hostile by definition) at every
boundary:

| Failure | What happens |
|---|---|
| `ep.load()` raises `ImportError` | warning logged, plugin skipped, **no** other plugin affected |
| `Plugin.__init__()` raises | warning logged, plugin skipped, **no** other plugin affected |
| `register()` raises | warning logged, plugin's hooks are *not* registered, **no** other plugin affected |
| `Plugin.__init_subclass__` fails | the subclass itself never becomes usable; the loader treats it as not-a-Plugin |
| `tn_venv.plugins` itself raises (e.g. a typo in the loader code) | re-raises — this *is* a tn-venv bug |

The warning goes through the `Reporter` passed to `load_plugins`.
Programmatic callers usually pass `reporter=SILENT` to silence
noise; the CLI passes the real reporter so users see failures.

## Where the loader runs

The loader runs **eagerly** at the top of `tn_venv.cli.cli_run`,
before argparse sees the argv. The eager load is what lets a plugin
that wraps `tn_venv.cli.cli_run` (e.g. the `tn-venv-gui` package
installing its `gui` subcommand) intercept argv like
`tn-venv gui --help` before argparse sees the help flag. Cost is
small — only the built-in plugin is loaded in the common case.

The eager load is paired with a lazy fallback in
`_Parser.format_help` so hosts that print help without going through
`cli_run` (rare but possible — think embedded uses) still get the
plugin summary block.

## Programmatic use

```python
from tn_venv.plugins import load_plugins
from tn_venv.report import Reporter

# Load every plugin and dump each one, with the reporter silenced:
registry = load_plugins(reporter=SILENT)

# Or pass a custom env so tests don't pick up the user's
# TN_VENV_PLUGINS by accident:
registry = load_plugins(reporter=Reporter(verbosity=0), env={})
```

The returned `HookRegistry` is fresh on every call. Don't cache it
across `load_plugins()` invocations — reloading is the documented
way to re-discover plugins (e.g. after installing a new package at
runtime, before invoking `run_session` again).

## Edge cases worth knowing

1. **A plugin class with empty `name`** is treated as a private
   base and **not** instantiated. This lets you write `class
   _Base(Plugin): pass` followed by `class Concrete(_Base): name =
   "concrete"` without `_Base` shadowing `Concrete`.
2. **Duplicate classes across modules** are deduplicated. So
   `tn_venv_demo_plugin:DemoPlugin` in two different distributions
   results in exactly one `DemoPlugin` being loaded.
3. **`Plugin()` instance passed via `TN_VENV_PLUGINS`** is used as
   — not reinstantiated. Useful for unit tests that want a
   pre-configured instance.
4. **A package that ships only entry points, no `tn_venv.plugins`
   key**, is silently ignored. Removing the key entirely is fine;
   no marker file is required.