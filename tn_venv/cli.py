"""Command line interface: ``tn-venv [OPTIONS] [DEST]``.

With no arguments at all it creates ``./.venv`` — one command, sane
defaults; every behaviour can be tuned through flags, ``TN_VENV_*``
environment variables, or a config file.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .config import find_default_config, load_env_config, load_file_config
from .config.spec import OPTION_SPECS, OptionSpec
from .errors import ConfigError, TnVenvError
from .report import Reporter
from .session import Options, merge_config, run_session
from .version import __version__

PROG = "tn-venv"

_EPILOG = """\
configuration precedence: CLI > TN_VENV_* env vars > config file > defaults.

examples:
  tn-venv                          create ./.venv with pip, current Python
  tn-venv .venv -p 3.12            pick a specific interpreter version
  tn-venv /tmp/x --system-site-packages
  tn-venv --with requests -r dev-requirements.txt
  tn-venv --setuptools --wheel --pip latest --upgrade-pip
  tn-venv --no-pip --activators powershell,batch
  tn-venv --list-pythons           show every interpreter tn-venv can find
"""


class _Parser(argparse.ArgumentParser):
    # pyrefly: ignore [bad-override]
    def error(self, message: str) -> None:  # type: ignore[override]  # exit code 2 with clean message
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")

    def format_help(self) -> str:  # type: ignore[override]
        # Append whatever plugins want to advertise. Plugins are loaded
        # lazily here so a normal ``tn-venv .venv`` invocation never
        # pays the cost — only ``--help`` triggers the plugin system.
        extra = _collect_plugin_help_epilog()
        if extra:
            sep = "" if (self.epilog or "").endswith("\n") else "\n"
            self.epilog = (self.epilog or "") + sep + extra
        return super().format_help()


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog=PROG,
        description="Create a Python virtual environment — batteries included. "
        "Running bare '%s' creates ./.venv with sensible defaults." % PROG,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "dest",
        nargs="?",
        default=None,
        metavar="DEST",
        help="destination directory for the environment (default: .venv)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    groups = {
        "interpreter options": {"python"},
        "creator options": {
            "clear",
            "upgrade",
            "system_site_packages",
            "symlinks",
            "copies",
            "scm_ignore",
        },
        "seeder options": {
            "seeder",
            "no_pip",
            "pip",
            "upgrade_pip",
            "setuptools",
            "wheel",
            "extra_search_dir",
            "offline",
            "seed_packages",
            "requirements",
        },
        "activation options": {"activators", "prompt"},
        "misc": {
            "quiet",
            "verbose",
            "color",
            "list_pythons",
            "list_plugins",
            "dry_run",
            "config",
            "no_config",
        },
    }
    group_objs: dict[str, argparse._ArgumentGroup] = {}
    for title in groups:
        group_objs[title] = parser.add_argument_group(title)

    for spec in OPTION_SPECS.values():
        title = next((t for t, dests in groups.items() if spec.dest in dests), "misc")
        _add_option(group_objs[title], spec)
    return parser


def _add_option(group: argparse._ArgumentGroup, spec: OptionSpec) -> None:
    kwargs: dict = {"dest": spec.dest, "help": spec.help, "default": None}
    flags = list(spec.flags)
    if spec.kind == "bool":
        # flags that are already negative (--no-pip) cannot take --no- prefixes
        negative = any(f.startswith(("--no-", "--without")) for f in flags)
        kwargs["action"] = "store_true" if negative else argparse.BooleanOptionalAction
    elif spec.kind == "count":
        kwargs["action"] = "count"
    elif spec.kind == "append":
        kwargs["action"] = "append"
        kwargs["metavar"] = spec.metavar
    elif spec.kind == "optional_str":
        kwargs["nargs"] = "?"
        kwargs["const"] = spec.optional_const
        kwargs["metavar"] = spec.metavar
    else:
        kwargs["metavar"] = spec.metavar
    if spec.choices and spec.kind not in ("bool", "count"):
        kwargs["choices"] = spec.choices
    group.add_argument(*flags, **kwargs)


def _cli_values(namespace: argparse.Namespace) -> dict[str, object]:
    values = vars(namespace)
    out: dict[str, object] = {}
    for dest, value in values.items():
        if dest == "dest":
            continue
        if value is None:
            continue
        out[dest] = value
    return out


def _resolve_options(
    args: argparse.Namespace, environ: dict[str, str] | None = None
) -> Options:
    environ = environ if environ is not None else dict(os.environ)
    cli = _cli_values(args)
    if cli.get("no_config"):
        env_cfg: dict[str, object] = {}
        file_cfg: dict[str, object] = {}
        config_path = None
    else:
        env_cfg = load_env_config(environ)
        explicit = cli.get("config") or environ.get("TN_VENV_CONFIG_FILE")
        # pyrefly: ignore [bad-argument-type]
        config_path = Path(explicit).expanduser() if explicit else find_default_config()  # type: ignore[arg-type]
        file_cfg = load_file_config(config_path)
    merged = merge_config(cli, env_cfg, file_cfg)
    dest = args.dest or ".venv"
    options = Options.from_mapping(merged)
    options.dest = Path(dest).expanduser()
    options.command = _render_command(dest)
    if config_path is not None:
        object.__setattr__(options, "config_file", config_path)  # informational
    return options


def _render_command(dest: str) -> str:
    argv = [sys.executable, "-m", "tn_venv", *[a for a in sys.argv[1:] if a != ""]]
    if dest not in argv:
        argv.append(dest)
    return " ".join(argv)


def _list_pythons(reporter: Reporter) -> int:
    from .discovery import discover_all

    reporter.step("discovering interpreters…")
    found = discover_all(report=reporter)
    if not found:
        reporter.warn("no interpreters found")
        return 1
    width = max(len(f"{info.version_str} ({info.bits}-bit)") for info, _ in found)
    for info, source in found:
        ver = f"{info.version_str} ({info.bits}-bit)"
        line = f"  {reporter.style(ver.ljust(width), 'em')}  {info.executable}"
        if info.gil_disabled:
            line += "  [free-threaded]"
        line += f"  — {source}"
        reporter.info(line)
    return 0


def _collect_plugin_help_epilog() -> str:
    """Run the plugin loader and concatenate HELP_EPILOG listeners.

    This is intentionally separate from :func:`_list_plugins` because
    it runs during ``format_help``, before any reporter or verbosity
    is configured. Errors are swallowed by the registry, so a broken
    plugin cannot break ``--help``.

    A built-in summary section ("Plugins:") is always prepended so
    users see what got loaded even when no plugin opts into the
    HELP_EPILOG hook. Plugins that want richer text can still
    register their own HELP_EPILOG listener; their output is
    appended after the summary.
    """
    from .plugins import HookName, load_plugins
    from .report import SILENT

    try:
        registry = load_plugins(reporter=SILENT)
    except Exception:  # noqa: BLE001 - never let plugin load break --help
        return ""

    parts: list[str] = [_plugin_summary_for_help(registry)]
    extra = registry.collect_help_epilog()
    if extra:
        parts.append(extra)
    return "\n\n".join(p for p in parts if p)


def _plugin_summary_for_help(registry) -> str:
    """Render the auto-generated ``Plugins:`` block for ``--help``.

    Lists every loaded plugin (by ``name``) with the comma-separated
    set of hooks it subscribed to. Plugins with no hooks (e.g. CLI
    subcommand installers) appear as ``name (no hooks)``.

    Note: ``HELP_EPILOG`` listeners are deliberately excluded from
    the comma-separated hook list (they don't fire during a real
    session — they only render text at ``--help`` time). A plugin
    that registered *only* a ``HELP_EPILOG`` still appears here so
    users can see who is contributing to their help text.
    """
    from .plugins import HookName

    # Collect owner -> set-of-hooks. Owners come from _owners; plugins
    # that registered no real hooks live in _hookless_plugins.
    by_name: dict[str, set[str]] = {}
    for hook in HookName:
        for listener in registry._listeners[hook]:  # type: ignore[attr-defined]
            owner = registry._owners.get(id(listener.fn))  # type: ignore[attr-defined]
            if owner is None:
                continue
            name = getattr(owner, "name", "") or type(owner).__name__
            if hook is not HookName.HELP_EPILOG:
                by_name.setdefault(name, set()).add(hook.value)
            else:
                # HELP_EPILOG doesn't show in the comma-separated list
                # but the plugin still needs a row.
                by_name.setdefault(name, set())
    # Hookless plugins: those that registered no hooks at all.
    for plugin in registry._hookless_plugins:  # type: ignore[attr-defined]
        name = getattr(plugin, "name", "") or type(plugin).__name__
        by_name.setdefault(name, set())

    if not by_name:
        return ""

    width = max(len(name) for name in by_name)
    lines = ["Plugins:"]
    for name in sorted(by_name):
        hooks = by_name[name]
        if hooks:
            lines.append(f"  {name.ljust(width)}  {', '.join(sorted(hooks))}")
        else:
            lines.append(f"  {name.ljust(width)}  (no hooks)")
    return "\n".join(lines)


def _list_plugins(reporter: Reporter) -> int:
    """Print every loaded plugin and the hooks it registered.

    Returns 0 on success, 1 when no plugins were loaded (which itself
    is not an error — only an empty list).
    """
    from .plugins import HookName, load_plugins

    reporter.step("discovering plugins…")
    registry = load_plugins(reporter=reporter)

    # Group listeners by plugin_name so the output reads one row per
    # plugin. Listeners with an empty plugin_name fall back to the
    # function's qualname (which is what load_plugins actually stores
    # for plugins that didn't pass ``plugin_name`` to ``hooks.add``).
    by_plugin: dict[str, list[str]] = {}
    for hook in HookName:
        for listener in registry._listeners[hook]:  # type: ignore[attr-defined]
            key = listener.plugin_name or listener.fn.__qualname__
            by_plugin.setdefault(key, []).append(hook.value)
    # Also fold in plugins whose ``register()`` ran but added no hooks
    # — without this, side-effect-only plugins (CLI subcommand shims,
    # post-creation installers, etc.) would be invisible. We dedup
    # against by_plugin by name.
    for plugin in registry._hookless_plugins:  # type: ignore[attr-defined]
        name = getattr(plugin, "name", "") or type(plugin).__name__
        by_plugin.setdefault(name, [])

    if not by_plugin:
        reporter.info("no plugins loaded")
        return 1

    # Recover each plugin's source via the owner map populated by
    # ``load_plugins`` during registration. Two passes: one for
    # plugins that registered at least one hook (tracked by the
    # ``_owners`` dict keyed on listener id), and one for plugins
    # whose ``register()`` ran but added nothing (CLI shims,
    # subcommand installers, etc.).
    sources: dict[str, str] = {}
    seen: set[int] = set()
    for hook in HookName:
        for listener in registry._listeners[hook]:  # type: ignore[attr-defined]
            owner = registry._owners.get(id(listener.fn))  # type: ignore[attr-defined]
            if owner is None or id(owner) in seen:
                continue
            seen.add(id(owner))
            name = getattr(owner, "name", "") or type(owner).__name__
            source = getattr(owner, "_tn_venv_source", None)
            if source is not None:
                sources[name] = f"{source.kind}: {source.spec}"
            else:
                sources[name] = "unknown"
    for plugin in registry._hookless_plugins:  # type: ignore[attr-defined]
        if id(plugin) in seen:
            continue
        seen.add(id(plugin))
        name = getattr(plugin, "name", "") or type(plugin).__name__
        source = getattr(plugin, "_tn_venv_source", None)
        if source is not None:
            sources[name] = f"{source.kind}: {source.spec}"
        else:
            sources[name] = "unknown"

    width = max(len(name) for name in by_plugin)
    for name in sorted(by_plugin):
        hooks_str = ", ".join(sorted(by_plugin[name]))
        line = (
            f"  {reporter.style(name.ljust(width), 'em')}"
            f"  hooks: {hooks_str or '(none)'}\n"
            f"  {'':>{width}}  source: {sources.get(name, 'unknown')}"
        )
        reporter.info(line)
    return 0


def cli_run(
    args: list[str] | None = None, *, environ: dict[str, str] | None = None
) -> int:
    """Programmatic entry point; returns a process exit code.

    Plugins are loaded *eagerly* (before ``parse_args``) so a plugin
    that wants to contribute to ``tn-venv --help`` (via the
    ``HELP_EPILOG`` hook) or to install a CLI subcommand (via a
    monkey-patch on ``tn_venv.cli.cli_run``) gets a chance to do so
    before argparse short-circuits on ``-h``/``--help``.

    Once the eager load has run, ``cli_run`` itself is re-invoked if
    a plugin replaced it. This makes subcommand dispatching
    (e.g. ``tn-venv gui --help``) work on the first invocation that
    triggers plugin loading.
    """
    # ``original_cli_run`` captures the *function object this frame
    # is bound to*. Without this we cannot detect a plugin's
    # monkey-patch, because inside the function body the bare name
    # ``cli_run`` resolves to the *current* module attribute (which
    # the patch may have replaced).
    original_cli_run = cli_run  # noqa: F841 (used below)

    # Force plugin loading. The cost is small: only the built-in
    # plugin is loaded in the common case.
    try:
        from .plugins import load_plugins
        from .report import SILENT

        load_plugins(reporter=SILENT)
    except Exception:  # noqa: BLE001 - never let a plugin break the CLI
        pass
    else:
        # If a plugin replaced ``tn_venv.cli.cli_run``, re-invoke
        # through the (now-patched) module attribute so the plugin's
        # dispatcher runs. This is how ``tn-venv gui --help`` works:
        # the eager load above installs the gui subcommand's patch
        # on cli_run, and we route the rest of the call through it.
        import tn_venv.cli as _self

        if _self.cli_run is not original_cli_run:
            return _self.cli_run(args=args, environ=environ)
        del _self

    parser = build_parser()
    namespace = parser.parse_args(args)

    # verbosity needed before option resolution for early messages
    verbosity = 1 + int(namespace.verbose or 0) - int(namespace.quiet or 0)
    reporter = Reporter(verbosity=max(0, min(3, verbosity)), color=namespace.color)

    try:
        if namespace.list_pythons:
            return _list_pythons(reporter)
        if namespace.list_plugins:
            return _list_plugins(reporter)
        options = _resolve_options(namespace, environ)
        if namespace.dry_run:
            _print_dry_run(options, reporter)
            return 0
        result = run_session(options, reporter)
    except ConfigError as exc:
        reporter.error(str(exc))
        return 2
    except TnVenvError as exc:
        reporter.error(str(exc))
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        reporter.error("interrupted")
        return 130
    return 0


def _print_dry_run(options: Options, reporter: Reporter) -> None:
    reporter.step("resolved configuration (dry run — nothing created)")
    for field_name, field_def in options.__dataclass_fields__.items():  # type: ignore[attr-defined]
        value = getattr(options, field_name)
        reporter.info(f"  {field_name:24} = {value!r}")


def main() -> None:
    """Console-script entry point (``tn-venv``).

    Looks ``cli_run`` up via the module attribute at call time rather
    than binding it at definition time, so plugins that monkey-patch
    ``tn_venv.cli.cli_run`` after this module was imported (such as
    ``tn-venv-gui`` installing its ``gui`` subcommand) are honoured.
    """
    import tn_venv.cli as _self

    raise SystemExit(_self.cli_run())


if __name__ == "__main__":  # pragma: no cover
    main()
