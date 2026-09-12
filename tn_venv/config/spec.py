"""Single source of truth for every tn-venv option.

The CLI parser, the environment-variable loader and the config-file loader
are all driven by :data:`OPTION_SPECS`, so a new option only ever needs to
be declared once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..errors import ConfigError

_TRUE = {"1", "true", "yes", "on", "y", "t"}
_FALSE = {"0", "false", "no", "off", "n", "f", ""}


@dataclass(frozen=True)
class OptionSpec:
    dest: str
    flags: tuple[str, ...] = ()
    kind: str = "str"  # str | bool | int | append | count | optional_str
    default: Any = None
    help: str = ""
    choices: tuple[str, ...] | None = None
    metavar: str | None = None
    env: str | None = None  # explicit env var override
    optional_const: str | None = None  # const value for optional_str flags
    cli_only: bool = False  # never read from env / config files

    @property
    def env_name(self) -> str:
        return self.env or "TN_VENV_" + self.dest.upper()

    @property
    def config_key(self) -> str:
        return self.dest.replace("_", "-")


SPECS: tuple[OptionSpec, ...] = (
    # -- interpreter ---------------------------------------------------------
    OptionSpec(
        "python",
        ("-p", "--python"),
        kind="append",
        help="Python interpreter to build the environment from: a path, "
        "a version (3, 3.12, 3.12.1), a name (python3.12, pypy3.10) or a "
        "PEP 514-ish tag. Repeatable — first match wins. Default: the "
        "interpreter running tn-venv.",
        metavar="SPEC",
    ),
    # -- creator ---------------------------------------------------------------
    OptionSpec(
        "clear",
        ("--clear",),
        kind="bool",
        default=False,
        help="delete the destination directory before creating the environment",
    ),
    OptionSpec(
        "upgrade",
        ("--upgrade",),
        kind="bool",
        default=False,
        help="upgrade an existing environment in place (keep installed packages)",
    ),
    OptionSpec(
        "system_site_packages",
        ("--system-site-packages",),
        kind="bool",
        default=False,
        help="give the environment access to the system site-packages",
    ),
    OptionSpec(
        "symlinks",
        ("--symlinks",),
        kind="bool",
        default=None,
        help="symlink the interpreter binaries instead of copying (default on POSIX)",
    ),
    OptionSpec(
        "copies",
        ("--copies",),
        kind="bool",
        default=None,
        help="copy the interpreter binaries instead of symlinking (default on Windows)",
    ),
    OptionSpec(
        "scm_ignore",
        ("--scm-ignore",),
        kind="str",
        default="git",
        choices=("git", "none"),
        help="write a source-control ignore file into the environment (default: git)",
    ),
    # -- seeder ------------------------------------------------------------------
    OptionSpec(
        "seeder",
        ("--seeder",),
        kind="str",
        default="pip",
        choices=("pip", "none"),
        help="package installer to seed the environment with (default: pip)",
    ),
    OptionSpec(
        "no_pip",
        ("--no-pip", "--without-pip"),
        kind="bool",
        default=False,
        help="do not install pip (shorthand for --seeder none)",
    ),
    OptionSpec(
        "pip",
        ("--pip",),
        kind="optional_str",
        optional_const="latest",
        default=None,
        metavar="VERSION",
        help="pip version to install: omit value for the latest release, "
        "pass a version to pin (e.g. --pip 24.0); default: bundled ensurepip version",
    ),
    OptionSpec(
        "upgrade_pip",
        ("--upgrade-pip",),
        kind="bool",
        default=False,
        help="upgrade pip to the latest release from the package index",
    ),
    OptionSpec(
        "setuptools",
        ("--setuptools",),
        kind="optional_str",
        optional_const="latest",
        default=None,
        metavar="VERSION",
        help="install setuptools (optionally pinned); not bundled on Python >= 3.12",
    ),
    OptionSpec(
        "wheel",
        ("--wheel",),
        kind="optional_str",
        optional_const="latest",
        default=None,
        metavar="VERSION",
        help="install wheel (optionally pinned)",
    ),
    OptionSpec(
        "extra_search_dir",
        ("--extra-search-dir",),
        kind="append",
        default=None,
        metavar="DIR",
        help="additional directories to search for wheels/sdists "
        "(PIP_FIND_LINKS); repeatable",
    ),
    OptionSpec(
        "offline",
        ("--offline",),
        kind="bool",
        default=False,
        help="do not reach the network: only use bundled wheels and "
        "--extra-search-dir locations (PIP_NO_INDEX)",
    ),
    OptionSpec(
        "seed_packages",
        ("--with", "--seed-package"),
        kind="append",
        default=None,
        env="TN_VENV_SEED_PACKAGES",
        metavar="PKG",
        help="install extra packages into the environment after seeding; "
        "any pip requirement specifier works; repeatable",
    ),
    OptionSpec(
        "requirements",
        ("-r", "--requirements"),
        kind="append",
        default=None,
        metavar="FILE",
        help="pip requirements file(s) to install after seeding; repeatable",
    ),
    # -- activators ------------------------------------------------------------------
    OptionSpec(
        "activators",
        ("--activators",),
        kind="append",
        default=None,
        metavar="LIST",
        help="comma separated activation scripts to generate "
        "(bash,batch,powershell,fish,csh,nushell,python, all, default, "
        "or -NAME to exclude); default: all supported",
    ),
    OptionSpec(
        "prompt",
        ("--prompt",),
        kind="str",
        default=None,
        help="custom prompt shown when the environment is active "
        "(default: the environment folder name)",
    ),
    # -- behaviour ----------------------------------------------------------------------
    OptionSpec(
        "quiet",
        ("-q", "--quiet"),
        kind="count",
        default=None,
        help="reduce verbosity (repeatable)",
        cli_only=False,
    ),
    OptionSpec(
        "verbose",
        ("-v", "--verbose"),
        kind="count",
        default=None,
        help="increase verbosity (repeatable)",
    ),
    OptionSpec(
        "color",
        ("--color",),
        kind="bool",
        default=None,
        help="force colored output on (use --no-color to force off)",
    ),
    OptionSpec(
        "list_pythons",
        ("--list-pythons",),
        kind="bool",
        default=False,
        help="list all discoverable interpreters and exit",
        cli_only=True,
    ),
    OptionSpec(
        "dry_run",
        ("--dry-run",),
        kind="bool",
        default=False,
        help="print the resolved configuration without creating anything",
        cli_only=True,
    ),
    OptionSpec(
        "config",
        ("--config",),
        kind="str",
        default=None,
        help="path to a config file (pyproject.toml / tn-venv.ini)",
        cli_only=True,
    ),
    OptionSpec(
        "no_config",
        ("--no-config",),
        kind="bool",
        default=False,
        help="ignore config files and environment variables",
        cli_only=True,
    ),
)

OPTION_SPECS: dict[str, OptionSpec] = {s.dest: s for s in SPECS}


def coerce_value(spec: OptionSpec, value: Any) -> Any:
    """Coerce a raw env-var / config-file value to the option's type."""
    if value is None:
        return None
    try:
        if spec.kind == "bool":
            if isinstance(value, bool):
                return value
            low = str(value).strip().lower()
            if low in _TRUE:
                return True
            if low in _FALSE:
                return False
            raise ValueError(f"expected a boolean, got {value!r}")
        if spec.kind == "int":
            return int(value)
        if spec.kind == "count":
            return int(value)
        if spec.kind == "append":
            if isinstance(value, (list, tuple)):
                return [str(v) for v in value]
            return [part.strip() for part in str(value).split(",") if part.strip()]
        if spec.kind == "optional_str":
            if isinstance(value, bool):
                return spec.optional_const if value else None
            return str(value)
        # plain str
        if spec.choices:
            val = str(value)
            if val not in spec.choices:
                raise ValueError(
                    f"expected one of {', '.join(spec.choices)}, got {val!r}"
                )
            return val
        return str(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"invalid value for option {spec.dest!r}: {exc}") from exc
