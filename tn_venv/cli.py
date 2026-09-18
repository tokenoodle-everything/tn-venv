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
    def error(self, message: str) -> None:  # exit code 2 with clean message
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


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
        config_path = Path(explicit).expanduser() if explicit else find_default_config()
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


def cli_run(
    args: list[str] | None = None, *, environ: dict[str, str] | None = None
) -> int:
    """Programmatic entry point; returns a process exit code."""
    parser = build_parser()
    namespace = parser.parse_args(args)

    # verbosity needed before option resolution for early messages
    verbosity = 1 + int(namespace.verbose or 0) - int(namespace.quiet or 0)
    reporter = Reporter(verbosity=max(0, min(3, verbosity)), color=namespace.color)

    try:
        if namespace.list_pythons:
            return _list_pythons(reporter)
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
    """Console-script entry point (``tn-venv``)."""
    raise SystemExit(cli_run())


if __name__ == "__main__":  # pragma: no cover
    main()
