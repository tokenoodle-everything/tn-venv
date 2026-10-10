# CLI integration

Plugins get three hooks into the CLI: `tn-venv --list-plugins`,
`HELP_EPILOG` for customising `--help`, and the historical
"monkey-patch `cli_run` for subcommands" pattern. This page covers
all three.

## `tn-venv --list-plugins`

The flag loads every plugin via `load_plugins()` and prints a table.
The output has three columns: plugin name, comma-separated hook list,
and provenance (built-in / entry-point: NAME=SPEC / env: VAR).

Example:

```text
$ tn-venv --list-plugins
==> discovering plugins…
  version_stamp      hooks: post_activators
                     source: built-in: VersionStampPlugin
```

Plugins whose `register()` ran without calling `hooks.add` show up
as `(no hooks)` so they're not silently invisible. The plugin
**name** comes from `Plugin.name` (or the class name if you don't
set it). The **hook list** comes from `HookRegistry`'s internal
listener map. The **source** comes from the private
`Plugin._tn_venv_source` attribute set by `load_plugins` — see
{doc}`authoring` for the dataclass.

Implementation details:

- The flag is `cli_only=True` — it short-circuits before option
  resolution. You cannot combine it with `--config` or any
  config-file lookup. This is intentional: `--list-plugins` should
  always print *something*, regardless of how broken the user's
  config file is.
- The flag itself prints to `stdout`. Warnings (e.g. a plugin
  failed to import) print to `stderr`. They never go to the same
  stream; you can grep `tn-venv --list-plugins` cleanly.
- `--list-plugins` returns 0 if any plugin loaded, 1 if none did.
  "None" means no plugins at all, including the built-ins, which
  is unusual but possible in a hostile environment.

## `HELP_EPILOG` — customising `tn-venv --help`

`HELP_EPILOG` is the public way for plugins to append text to
`tn-venv --help` output. The listener takes no arguments and
returns a `str` (or `None` to opt out). Multiple `HELP_EPILOG`
listeners are concatenated with blank-line separators and appear
*after* the auto-generated `Plugins:` block:

```text
$ tn-venv --help
... argparse output ...

configuration precedence: ...

examples:
  tn-venv                       ...

Plugins:                    ← auto-generated
  plugin_a        hooks: ...
  plugin_b        hooks: ...

extras from plugin_c:       ← HELP_EPILOG contribution
  mycmd    run my custom command

Run 'tn-venv help plugin_c' for details on its subcommands.
```

To register:

```python
from tn_venv.plugins import HookName, Plugin


class HelpAdder(Plugin):
    name = "help_adder"

    def register(self, hooks):
        def _epilog():
            return (
                "extras from help_adder:\n"
                "  mycmd    run my custom command\n"
            )
        hooks.add(HookName.HELP_EPILOG, _epilog, plugin_name=self.name)
```

Rules:

- The listener must return a `str` (or `None` to opt out). Empty
  string is treated as opt-out.
- tn-venv **always** appends the auto-generated `Plugins:` block
  first. `HELP_EPILOG` is only for **extra** text the plugin wants
  to advertise (subcommand menus, examples, status pages, etc.).
- Listener failures are caught and reported at warning level; they
  never break `--help`.
- Plugins are loaded **eagerly** at the top of `cli_run` (not
  just when `--help` is requested). The eager load is what lets a
  plugin that wraps `cli_run` (e.g. `tn-venv-gui`) intercept
  argv like `tn-venv gui --help` before argparse sees the help
  flag. Cost is small — only the built-in plugin is loaded in the
  common case.

The legacy way to do this was to monkey-patch
`tn_venv.cli.build_parser` and append to `parser.epilog`. New
plugins should prefer `HELP_EPILOG` — it's stable, public, and
doesn't depend on argparse internals.

## Adding a CLI subcommand

The clean way to add `tn-venv gui ...` (or any other subcommand) is:

1. Add a `HELP_EPILOG` listener that documents the subcommand in
   `tn-venv --help` output.
2. In `register()`, monkey-patch `tn_venv.cli.cli_run` to dispatch
   the subcommand before argparse sees the argv.

The `tn-venv-gui` package is the canonical example. Its
`GuiSubcommandPlugin.register()` does both:

```python
def register(self, hooks):
    if os.environ.get("TN_VENV_GUI_NO_AUTOLOAD"):
        return
    # 1. Install the subcommand dispatch — wraps tn_venv.cli.cli_run.
    subcommand.install_subcommand()
    # 2. Contribute to --help output via the public hook.
    hooks.add(HookName.HELP_EPILOG, _gui_help_epilog, plugin_name=self.name)
```

The `install_subcommand()` function does the wrapper install.
The mechanism:

1. `install_subcommand()` saves a reference to the **current**
   `tn_venv.cli.cli_run` (let's call it `_ORIGINAL`).
2. It installs a `_patched` function as the new `tn_venv.cli.cli_run`.
3. `_patched` inspects `sys.argv[1:]` (or the explicit `args`
   argument). If `argv[0]` is a known subcommand name (`gui`),
   it dispatches to the subcommand's handler. Otherwise it
   delegates to `_ORIGINAL`.
4. The dispatch is **idempotent**: subsequent invocations are
   no-ops, so calling `install_subcommand()` from `register()`
   (which runs every time `load_plugins()` is called) doesn't
   double-wrap.

The wrapper pattern works because of two design choices in
tn-venv itself:

- `cli_run` is loaded **eagerly** at the top of `cli_run` itself,
  *before* argparse sees the argv. So the wrapper is installed
  before argparse parses `tn-venv gui --help`.
- `main()` (the console-script entry point) looks `cli_run` up on
  its own module at call time, so a plugin's monkey-patch is
  honoured even when `main` was imported before the patch was
  applied.

The catch is that the wrapper patch **only ever** runs on the *next*
invocation. Inside the invocation where the patch installs itself,
`cli_run` is already executing the *original* function frame;
`cli_run` handles that by capturing the original `cli_run`
reference at function entry (`original_cli_run`) and re-invoking
through the (now-patched) module attribute if `_self.cli_run is not
original_cli_run`. So `tn-venv gui --help` works on the first
invocation, not just subsequent ones.

### Why this is transitional

Monkey-patching `tn_venv.cli.cli_run` couples your plugin to
argparse internals and to the structure of the existing CLI. We
keep it as a supported path because it's the simplest way to add
subcommands today, but a future release may add a more structured
"subcommand" registration. If you can avoid the monkey-patch
(e.g. by relying on `HELP_EPILOG` alone), do.

### A minimal subcommand plugin

```python
"""A minimal ``tn-venv hello`` subcommand."""

from __future__ import annotations

import sys
from typing import Sequence

from tn_venv.plugins import HookName, Plugin


HELLO_EPILOG = """

text: hello world subcommand

Run 'tn-venv hello --help' for details.
"""


def _hello(args: Sequence[str]) -> int:
    if "--help" in args or "-h" in args:
        sys.stdout.write(HELLO_EPILOG)
        return 0
    sys.stdout.write("hello from tn-venv!\n")
    return 0


class HelloPlugin(Plugin):
    name = "hello"

    def register(self, hooks) -> None:
        # Document the subcommand in --help output.
        hooks.add(HookName.HELP_EPILOG, lambda: HELLO_EPILOG, plugin_name=self.name)

        # Install the subcommand dispatcher.
        try:
            from tn_venv import cli as _cli
            if getattr(_cli.cli_run, "_hello_installed", False):
                return
            original = _cli.cli_run

            def _patched(args=None, *, environ=None, **kw):
                argv = list(args) if args is not None else sys.argv[1:]
                if argv and argv[0] == "hello":
                    return _hello(argv[1:])
                return original(args, environ=environ, **kw)

            _patched._hello_installed = True  # type: ignore[attr-defined]
            _cli.cli_run = _patched
        except Exception:
            # Plugin loading must never raise.
            pass
```

This is intentionally small — it's the "hello world" of CLI
subcommands, not a template for production use. For a real
subcommand, follow the patterns in `tn-venv-gui`.

## Subcommand best practices

- **Idempotent installation.** Your monkey-patch must detect a
  previously-installed version (via a marker attribute on the
  wrapper) and no-op.
- **Help handling.** When the user passes `--help` or `-h` *after*
  the subcommand name, print your subcommand's help and return
  `0` without falling through to the original CLI.
- **Pass through unknown argv.** If `argv` doesn't start with your
  subcommand name, delegate to the original `cli_run`. Don't
  swallow args you don't recognise.
- **Exit codes.** Return `0` on success, non-zero on failure.
  Match the existing CLI's exit code conventions
  (see {doc}`../../reference/exit-codes`).
- **Respect `*_NO_AUTOLOAD` env vars.** The `tn-venv-gui` package
  honours `TN_VENV_GUI_NO_AUTOLOAD=1`. Pick a similar name for your
  own no-op switch and document it.

## What if my plugin needs a new CLI flag?

It can't, and shouldn't try. `--flag` and `--no-flag` live in
`tn_venv.config.spec`. To add a new flag, send a PR to `tn-venv`
itself. Adding CLI flags through a plugin would break `--dry-run`
output, config-file mapping, env-var mapping, and every other
piece of option plumbing — none of which are plugin-aware.

If you really need a one-off CLI flag for an internal tool, consider
using `tn-venv --with PKG` plus a seeder plugin instead. Seeders
are a separate extension mechanism — see
{doc}`../../development/extending`.