# Plugins

`tn-venv` has a small, deliberately narrow plugin system. It exists
for one job: letting third-party packages hook into the creation
pipeline (and the CLI) **without** monkey-patching `tn-venv`'s
internals. If you want to react to a virtual environment being created,
extend the CLI, or contribute to `--help`, you write a `Plugin`.

This directory is the **authoritative reference** for everything
plugin-shaped in tn-venv. The other docs (`docs/guide/plugins.md`,
`docs/reference/python-api.md`, `docs/reference/cli.md`,
`docs/development/architecture.md`) only point at it.

```{toctree}
:maxdepth: 1

quickstart
discovery
hooks
authoring
cli-integration
reference
```

## Contents at a glance

| Page | What it covers |
|---|---|
| {doc}`quickstart` | Minimal "write your first plugin" recipe. Start here. |
| {doc}`discovery` | How plugins are loaded (built-ins, entry points, `TN_VENV_PLUGINS`), deduplication, error isolation. |
| {doc}`hooks` | The six lifecycle hooks and the `HELP_EPILOG` hook: when they fire, what payload they get, and how priority works. |
| {doc}`authoring` | The full `Plugin` class API: `register()`, `HookContext`, `PluginSource`, `HookRegistry`. |
| {doc}`cli-integration` | `tn-venv --list-plugins`, customizing `--help` via `HELP_EPILOG`, monkey-patching `cli_run` for subcommands. |
| {doc}`reference` | One-screen API table for everything in `tn_venv.plugins`. |

## Public API surface

Everything below is importable from `tn_venv.plugins` and considered
backward-compatible. Anything not listed here is internal.

```python
from tn_venv.plugins import (
    # Discovery
    Plugin,                # base class — subclass and override register()
    load_plugins,          # build a populated HookRegistry
    parse_plugin_spec,     # split a TN_VENV_PLUGINS-style value
    require_plugin,        # look up a built-in by name

    # Hooks
    HookName,              # enum of all hook names
    HookContext,           # passed to every lifecycle-hook listener
    HookRegistry,          # dispatcher with priority + fault isolation

    # Provenance
    PluginSource,          # dataclass describing where a plugin came from

    # Constants
    PLUGIN_ENTRY_POINT,    # "tn_venv.plugins"
    PLUGIN_ENV_VAR,        # "TN_VENV_PLUGINS"
    DEFAULT_PRIORITY,      # 100

    # Built-ins
    VersionStampPlugin,    # writes tn-venv-version into pyvenv.cfg
)
```

The same names are also re-exported from `tn_venv` itself for
programmatic callers:

```python
from tn_venv import (
    Plugin, HookContext, HookName,
    VersionStampPlugin, load_plugins,
)
```

## When to use a plugin

Reach for a plugin when you want to:

- React to a virtual environment being created (`SESSION_START`,
  `SESSION_END`, …). Useful for emitting telemetry, stamping
  metadata into files, kicking off post-creation installers, etc.
- Add an extra `--flag` or `--no-prompt` — wait, you can't. Options
  live in `tn_venv.config.spec`. Use a **CLI subcommand** instead.
- Add a CLI subcommand like `tn-venv gui …`. Plugins that wrap
  `tn_venv.cli.cli_run` directly are supported but should be
  treated as a transitional API (see {doc}`cli-integration`).
- Customise the text printed by `tn-venv --help`. Use the
  `HELP_EPILOG` hook.

Reach for a **seeder** instead if you want to swap the package
installer (`uv`, `poetry`, …). Seeders are a separate extension
mechanism; see {doc}`../development/extending`.

## What plugins are *not*

Plugins are deliberately limited. They are **not**:

- A way to register new CLI flags. Option specs are static; if you
  need a new `--flag`, send a PR to `tn-venv.config.spec`.
- A way to swap the creator, the activator, or any other stage
  directly. Those have their own protocol.
- Threadsafe. The pipeline is single-threaded; concurrent calls
  from the same process are not supported.
- A remote-execution surface. Plugins run in-process, in the
  same interpreter that called `tn_venv.create_venv()`.

## Versioning policy

The plugin contract is part of `tn-venv`'s **public** API surface.
Anything documented here is covered by the project's
[versioning policy](../changelog.md) — i.e. breaking changes ship
behind a `0.x → 0.(x+1)` bump or `1.x.y → 1.(x+1).0`. The
`Plugin` class, `HookName` enum, `HookContext` dataclass, and
`HookRegistry` API will not break without a deprecation cycle.

The `Plugin._tn_venv_source` attribute **is** part of the public
API as of 1.1.0 (it's read by `tn-venv --list-plugins`), but the
leading underscore signals "set by the loader, not by the plugin
author". Plugins should treat it as read-only.