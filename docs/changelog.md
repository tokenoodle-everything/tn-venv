# Changelog

All notable changes to tn-venv are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `tn-venv --list-plugins` flag. Loads every plugin via the same
  discovery path as `run_session` (built-ins + entry points +
  `TN_VENV_PLUGINS`) and prints a table of plugin name, registered
  hooks, and provenance. Hookless plugins (CLI shims, subcommand
  installers, …) appear as `(no hooks)` so they are not silently
  invisible.
- `HookName.HELP_EPILOG` hook. Plugins can now append text to
  `tn-venv --help` output via a public hook instead of monkey-
  patching `argparse`. The listener takes no arguments and returns
  a string; tn-venv appends it after an auto-generated `Plugins:`
  block. Plugins are loaded eagerly by :func:`cli_run` so a plugin
  that wraps ``tn_venv.cli.cli_run`` (e.g. ``tn-venv-gui`` installing
  its ``gui`` subcommand) gets a chance to intercept argv like
  ``tn-venv gui --help`` before argparse sees the help flag.
- `PluginSource` dataclass exported from `tn_venv.plugins`. Every
  loaded plugin instance now carries a `_tn_venv_source` attribute
  describing where it came from (`built-in`,
  `entry-point: NAME=SPEC`, or `env: TN_VENV_PLUGINS`).
  `--list-plugins` consumes this; the attribute is private but the
  dataclass is part of the public API for callers who want to
  introspect plugins programmatically.

### Changed
- The plugin loader is now invoked **eagerly** at the top of
  `tn_venv.cli.cli_run` rather than lazily on `--help`.
  Plugins that replace ``tn_venv.cli.cli_run`` (e.g. the
  ``tn-venv-gui`` package installing its ``gui`` subcommand) now
  intercept argv like ``tn-venv gui --help`` on the very first
  invocation that triggers plugin loading. The lazy ``--help`
  trigger (via ``format_help``) is still in place as a belt-and-
  braces fallback for hosts that print help without going
  through ``cli_run``.
- ``main()`` looks up ``cli_run`` on its own module at call time
  instead of binding the name at definition time, so the
  console-script entry point picks up a plugin's monkey-patch
  even when ``main`` was imported before the patch was applied.

### Fixed
- ``tn-venv gui --help`` printed the full tn-venv help instead of
  the GUI subcommand's help. The cli_run monkey-patch installed
  by the plugin only ran on the *next* invocation, so argparse
  saw ``--help`` first and short-circuited before the wrapper
  could dispatch. Fixed by capturing the original ``cli_run``
  reference at the top of ``cli_run`` and re-invoking through
  the (now-patched) module attribute when the plugin has
  replaced the function.

- Plugin loader dropped every plugin past the first one. A module that
  declared `PLUGINS = [A, B, C]` only ever loaded `A`; the same bug
  affected comma-separated entries in `TN_VENV_PLUGINS` and
  entry points that pointed at modules rather than classes. The
  loader now returns `list[Plugin]` from every code path
  (`_from_module_attr`, `_from_entry_point`, `_resolve_target`) and
  propagates them up to `load_plugins`.
- `vars()` scan picked the first `Plugin` subclass it found, so a
  module that defined `class _Base(Plugin)` followed by
  `class Concrete(_Base)` loaded the empty-named base class instead
  of the concrete one — a silent no-op that hid user plugins.
  The scan now skips classes whose `name` is empty (the convention
  for abstract / helper bases) and exposes a dedicated
  `_scan_module_for_plugins` helper for the rule.
- Replaced `:class:`~tn_venv.…`` cross-references in
  `docs/guide/plugins.md` and `docs/development/architecture.md`
  with plain inline code. The docs site does not configure
  `sphinx.ext.autodoc`, so the references previously rendered as
  literal `<code>~tn_venv.…</code>` (with the leading tilde) and
  provided no linkability.

## Docs

- Moved the full plugin reference from a single page into a new
  `docs/plugins/` directory. `docs/guide/plugins.md` is now a
  navigation pointer; the authoritative reference lives at
  :doc:`plugins/index`.
- New pages under `docs/plugins/`: `index` (overview, public API
  table, when-to-use, versioning policy), `quickstart` (minimal
  end-to-end "write your first plugin" recipe, including the
  `pyproject.toml` entry-point snippet), `discovery` (built-ins /
  entry points / `TN_VENV_PLUGINS`, deduplication rules, failure
  isolation, programmatic use, edge cases), `hooks` (full reference
  for all six hooks — the five lifecycle hooks plus `HELP_EPILOG` —
  with `ctx.data` keys populated per stage, listener signatures,
  priority, fault isolation, recipes), `authoring` (the full
  `Plugin` / `HookRegistry` / `HookContext` / `PluginSource` API,
  including introspected members used by `--list-plugins`),
  `cli-integration` (`--list-plugins`, `HELP_EPILOG`, adding a CLI
  subcommand, the cli-run monkey-patch contract), `reference`
  (one-screen API table for everything in `tn_venv.plugins`).
- Slimmed plugin mentions in the rest of the docs to one-line
  references pointing at `docs/plugins/`:
  `docs/reference/python-api.md` (Plugin system section now lists
  the public symbols and links to the reference),
  `docs/reference/cli.md` (`--list-plugins` now points at the new
  CLI-integration page), `docs/reference/environment-variables.md`
  (`TN_VENV_PLUGINS` row now points at `docs/plugins/index`),
  `docs/development/extending.md` (the existing redirect at the top
  now points at `../plugins/...` instead of `../guide/plugins`).
- New plugin-registry page at `docs/plugins/community.md`.
  Plugin authors add their row by opening a PR; the four
  ratings (Maintenance / Stability / Documentation / Adoption,
  each 1-5 stars), the tier badge (Bronze / Silver / Gold /
  Platinum, derived from the average), the *Official Authorized*
  flag (granted only by the tn-venv team), and the last-reviewed
  date are filled in by the maintainers after merge. Shields.io
  badge URLs for every rating dimension are documented and the
  page also lays out the *Plugin of the Month*, *Rising Plugin*,
  and *Most Discussed* slots that will be filled in by the
  November 2026 monthly cycle. The `tn-venv-gui` row ships at
  Tier 4 (Platinum) with Official Authorized status; all
  subsequent rows must be added by maintainers, not by the
  plugin authors themselves.
- `docs/development/architecture.md` Plugin hooks section updated
  for the eager plugin load (see the [Changed] section above).
- `docs/guide/plugins.md` updated cross-reference (`{ref}`target)
  renamed `help-epilog-hook` to `help-epilog` to match the
  labelled section anchor.

## [1.0.0] — 2026-10-05 — 2026-10-05

### Added
- Plugin system under `tn_venv.plugins`: a `Plugin` base class, a
  priority-ordered `HookRegistry`, and a `load_plugins` loader that
  combines built-in plugins, third-party entry points in the
  `tn_venv.plugins` group, and the `TN_VENV_PLUGINS` environment
  variable. Five lifecycle hooks are emitted by `run_session`:
  `session_start`, `pre_create`, `post_activators`, `post_seed`,
  `session_end`.
- Built-in `VersionStampPlugin`: appends `tn-venv-version = <version>`
  to `pyvenv.cfg` after the activation scripts have been generated.
  Doubles as the worked example in the new `docs/guide/plugins.md`.
- `docs/guide/plugins.md` — user-facing tutorial covering discovery,
  hook semantics, and writing a plugin. The architecture and
  environment-variables references were updated to point at it.

### Fixed
- Fix the import for the `Plugin` class referenced in type annotations within the 
file `tn_venv/plugins/registry.py`. Change its import source from the 
`tn_venv.plugins.builtin`  module back to the original `tn_venv.plugins.api` module.

## [0.2.0] — 2026-10-02

### Added
- Add alias `TNError` back to public API.
- [mypy](https://mypy-lang.org/) static type checking, running alongside
  pyrefly: `[tool.mypy]` configuration in `pyproject.toml`, a
  `mypy-typecheck` GitHub Actions workflow, and `.mypy_cache/` added to
  `.gitignore`.
- pyrefly `project-excludes` covering `.venv`, `.github`, build outputs,
  `__pycache__`, and tests.
- [pyrefly](https://pyrefly.org/) static type checking: `[tool.pyrefly]`
  configuration in `pyproject.toml` and a `pyrefly-typecheck` GitHub
  Actions workflow.
- `CONTRIBUTORS` file listing core contributors.
  Closes [#2](https://github.com/tokenoodle-everything/tn-venv/issues/2).
- Version stamp (`Version: 1.0`) in `License.txt`.
- Full documentation site under `docs/` (Sphinx + MyST): user guide, CLI /
  env-var / config-file references, architecture and extension manuals,
  published to GitHub Pages.
- Expanded test suite: per-module coverage for discovery providers,
  creators, activators, seeder, config, and utilities.

### Changed
- The cmd.exe activation script (`activate.bat`) now carries a
  `rem generated by tn-venv` header comment.
- Rename ``TNError`` to ``TnVenvError``. The old name remains importable
  as a backwards-compatible alias.

### Fixed
- Fixes [#6](https://github.com/tokenoodle-everything/tn-venv/issues/6).
- Fixes [#7](https://github.com/tokenoodle-everything/tn-venv/issues/7).
- Fixes [#4](https://github.com/tokenoodle-everything/tn-venv/issues/4).
- Fixes [#5](https://github.com/tokenoodle-everything/tn-venv/issues/5).
  For the time being, comment out this constant.
- `Options.from_mapping` normalises explicit `None` values for list options
  (`python`, `extra_search_dir`, `seed_packages`, `requirements`,
  `activators`) to empty lists *before* filtering; previously the
  normalisation loop was dead code and could never run.
  Fixes [#8](https://github.com/tokenoodle-everything/tn-venv/issues/8).
- Fixes [#9](https://github.com/tokenoodle-everything/tn-venv/issues/9).
- Type errors reported by pyrefly and mypy in the discovery providers:
  `winreg` attribute access in `windows_registry`, and the
  `subprocess.run` overload, possibly-unbound variable, and regex
  match-group accesses in `py_launcher`.
- Type errors reported by mypy in `cli`, `report`, and
  `discovery.python_info`.
- Type errors reported by pyrefly in `cli` and `report`.
- Correct the `--dry-run` example output in the configuration guide.
  Fixes [#1](https://github.com/tokenoodle-everything/tn-venv/issues/1).
- Documentation build configuration (`docs/conf.py`,
  `docs/requirements.txt`).
- Contact email in `SECURITY.md`.

### Removed
- Unused import `dataclasses.field` in `tn_venv/config/spec.py`.

## [0.1.0] — 2026-09-12

Initial public release.

### Added
- One-command creation: bare `tn-venv` builds `./.venv` with pip installed.
- Interpreter discovery from PATH, the Windows registry (PEP 514), the `py`
  launcher (PEP 397), uv-managed installs, and pyenv; `-p` accepts paths,
  versions (`3.12`), command names, and implementation specs (`pypy3.10`).
- Platform-native creators: Windows copies `venvlauncher` redirectors with
  a real-binary + DLL fallback; POSIX symlinks with copy fallback.
- Seeding via `ensurepip`, with pip pinning (`--pip 24.0`), index upgrades
  (`--upgrade-pip`), `setuptools`/`wheel`, `--with PKG` and `-r FILE`
  installation at creation time, `--extra-search-dir`, and `--offline`.
- Activation scripts for bash/zsh, cmd.exe, PowerShell, fish, csh/tcsh,
  Nushell, plus `activate_this.py`.
- Layered configuration: CLI flags > `TN_VENV_*` environment variables >
  config files (`pyproject.toml`, `tn-venv.ini`, `.tn-venv.toml`,
  `setup.cfg`) > defaults; `--dry-run` to inspect the result.
- `--clear` / `--upgrade` lifecycle management with an inter-process file
  lock (stale-lock reclamation included).
- Python API: `tn_venv.create_venv()` and `tn_venv.cli_run()`.
