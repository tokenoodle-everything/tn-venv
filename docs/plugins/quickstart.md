# Quickstart

This page walks through writing, packaging, and loading your first
`tn-venv` plugin. By the end you will have a package that prints
a line every time `tn-venv` creates a virtual environment.

## What we are building

A package called `tn_venv_demo_plugin` that:

1. Registers itself as a `tn_venv.plugins` entry point.
2. Prints `hello from demo_plugin` at `SESSION_START`.
3. Captures the created environment's path at `SESSION_END`.

## Step 1 — the plugin module

Create the directory:

```text
tn_venv_demo_plugin/
└── src/
    └── tn_venv_demo_plugin/
        └── __init__.py
```

Write `src/tn_venv_demo_plugin/__init__.py`:

```python
"""A trivial tn-venv plugin."""

from __future__ import annotations

from tn_venv.plugins import HookName, Plugin


class DemoPlugin(Plugin):
    """Logs a line at session start and captures the env dir at session end."""

    # Stable identifier; required by Plugin. The loader emits this as
    # the "name" column in ``tn-venv --list-plugins`` output.
    name = "demo_plugin"

    def register(self, hooks) -> None:
        # Hooks.add() accepts either a callable directly or a
        # decorator; both forms are demonstrated here.
        hooks.add(
            HookName.SESSION_START,
            self._on_session_start,
            priority=100,           # DEFAULT_PRIORITY is 100
            plugin_name=self.name,
        )

        @hooks.add(HookName.SESSION_END, plugin_name=self.name)
        def _on_session_end(ctx):
            # SESSION_END is the only lifecycle hook where ctx.result
            # is guaranteed to be populated.
            env_dir = ctx.result.env_dir if ctx.result else None
            ctx.reporter.info(
                f"[demo_plugin] session ended; env_dir = {env_dir}"
            )
```

Three rules of thumb:

- `name` is required. Subclasses without a `name` attribute get
  the class name auto-assigned by `Plugin.__init_subclass__`, but
  you should set it explicitly so the name doesn't change if you
  rename the class later.
- `register()` runs once per `load_plugins()` call. Anything you
  put there runs at import-of-the-entry-point, before any
  `tn-venv` command runs.
- Listener return values are ignored (until the day we add a
  pipeline-short-circuiting hook). Communicate through
  `ctx.data`, `ctx.options`, or `ctx.result`.

## Step 2 — packaging metadata

Create `pyproject.toml` next to `src/`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "tn_venv_demo_plugin"
version = "0.1.0"
description = "A trivial tn-venv plugin"
requires-python = ">=3.11"

# The entry-point group "tn_venv.plugins" is a hard-coded constant
# (see tn_venv.plugins.PLUGIN_ENTRY_POINT). The value on the right
# is the dotted path to your class — same form as a normal
# ``module:Class`` Python import target.
[project.entry-points.tn_venv.plugins]
demo_plugin = "tn_venv_demo_plugin:DemoPlugin"

[tool.setuptools.packages.find]
where = ["src"]
```

The key (`demo_plugin`) is the entry-point name. It shows up in the
"source" column of `tn-venv --list-plugins`:

```text
demo_plugin         hooks: session_end, session_start
                    source: entry-point: demo_plugin=tn_venv_demo_plugin:DemoPlugin
```

The key (`demo_plugin`) is the entry-point name. It shows up in the
"source" column of `tn-venv --list-plugins`:

```text
demo_plugin         hooks: session_end, session_start
                    source: entry-point: demo_plugin=tn_venv_demo_plugin:DemoPlugin
```

## Step 3 — install and run

```bash
pip install -e .
tn-venv .venv
```

Expected output:

```text
==> creating virtual environment at ./.venv
interpreter: cpython 3.14.7 (64-bit) from /usr/bin/python3
hello from demo_plugin           # ← your plugin
==> environment ready: ./.venv/Scripts/python.exe
[demo_plugin] session ended; env_dir = ./.venv   # ← your plugin again
```

If you do not see your lines, run `tn-venv --list-plugins` and check
that `demo_plugin` is in the output. If it isn't, your entry point
isn't being advertised — see {doc}`discovery`.

## Step 4 — verify

```bash
tn-venv --list-plugins
```

Expected (with the built-in plugins):

```text
==> discovering plugins…
  demo_plugin         hooks: session_end, session_start
                      source: entry-point: demo_plugin=tn_venv_demo_plugin:DemoPlugin
  version_stamp       hooks: post_activators
                      source: built-in: VersionStampPlugin
```

That's it. You have a working plugin.

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `tn-venv --list-plugins` doesn't show your plugin | entry-point group or value typo | re-check `[project.entry-points."tn_venv.plugins"]`; the *group* uses underscores (`tn_venv.plugins`), the *target* uses dots |
| Plugin loads but no hook fires | you forgot to override `register()`, or your hook name is misspelled | `register()` must call `hooks.add(...)` at least once; hook names are the `HookName` enum members |
| `hello from demo_plugin` fires twice | both the entry-point loader and `TN_VENV_PLUGINS` are loading it | remove the duplicate, or rely on dedup-by-class |
| Plugin import fails silently | typo in the dotted path | run `python -c \"from tn_venv_demo_plugin import DemoPlugin\"` to confirm the path is importable |
| Plugin fires on `tn-venv --help` | expected — see {doc}`cli-integration` | if you don't want that, guard `register()` with an env-var |

## Next steps

- {doc}`discovery` — what the loader does behind the scenes.
- {doc}`hooks` — the full lifecycle hook reference.
- {doc}`authoring` — `register()`, `HookContext`, `PluginSource`, and the rest of the API.
- {doc}`cli-integration` — `HELP_EPILOG` and `tn-venv --list-plugins`.