"""Load configuration from files (pyproject.toml / tn-venv.ini / setup.cfg)
and from ``TN_VENV_*`` environment variables.

Resolution precedence (highest wins):

1. command line
2. environment variables
3. config file (``--config``, ``TN_VENV_CONFIG_FILE``, or discovered)
4. built-in defaults
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Any

from ..errors import ConfigError
from .spec import OPTION_SPECS, coerce_value

try:
    import tomllib
except ImportError:  # pragma: no cover - python < 3.11
    tomllib = None  # type: ignore[assignment]

_CONFIG_SECTION_NAMES = ("tool.tn-venv", "tn-venv", "tn_venv")
_DEFAULT_CANDIDATES = (
    "pyproject.toml",
    "tn-venv.ini",
    "tn_venv.ini",
    ".tn-venv.toml",
    "setup.cfg",
)


def find_default_config(start: Path | None = None) -> Path | None:
    """Locate a config file, searching *start* (default: CWD) and its parents."""
    start = (start or Path.cwd()).resolve()
    for directory in (start, *start.parents):
        for name in _DEFAULT_CANDIDATES:
            candidate = directory / name
            if not candidate.is_file():
                continue
            if name == "pyproject.toml":
                # only counts when it actually has our section
                try:
                    data = _read_toml(candidate)
                except ConfigError:
                    continue
                section = _extract_toml_section(data)
                if section is not None:
                    return candidate
                continue
            if name == "setup.cfg":
                parser = configparser.ConfigParser()
                try:
                    parser.read(candidate, encoding="utf-8")
                except configparser.Error:
                    continue
                if parser.has_section("tn_venv"):
                    return candidate
                continue
            return candidate
        # stop at a repository boundary so we do not climb forever
        if (directory / ".git").exists():
            break
    return None


def _read_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise ConfigError("TOML config files require Python 3.11+")
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read TOML config {str(path)!r}: {exc}") from exc


def _extract_toml_section(data: dict[str, Any]) -> dict[str, Any] | None:
    tool = data.get("tool")
    if isinstance(tool, dict):
        for key in ("tn-venv", "tn_venv"):
            section = tool.get(key)
            if isinstance(section, dict):
                return section
    # a dedicated .tn-venv.toml may hold options at the top level
    if data and not any(k in data for k in ("tool", "project", "build-system")):
        return data
    return None


def _read_ini(path: Path) -> dict[str, Any]:
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except configparser.Error as exc:
        raise ConfigError(f"cannot read INI config {str(path)!r}: {exc}") from exc
    for section in ("tn-venv", "tn_venv", "virtualenv"):
        if parser.has_section(section):
            return dict(parser.items(section))
    return {}


def load_file_config(path: Path | None) -> dict[str, Any]:
    """Read *path* and return a {dest: coerced_value} mapping."""
    if path is None:
        return {}
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {str(path)!r}")
    suffix = path.suffix.lower()
    if suffix == ".toml":
        raw = _extract_toml_section(_read_toml(path)) or {}
    else:
        raw = _read_ini(path)
    return _map_keys(raw, source=str(path))


def _map_keys(raw: dict[str, Any], *, source: str) -> dict[str, Any]:
    """Translate config keys (kebab-case) into option dests with coercion."""
    by_config_key = {
        spec.config_key: spec for spec in OPTION_SPECS.values() if not spec.cli_only
    }
    by_dest = {spec.dest: spec for spec in OPTION_SPECS.values() if not spec.cli_only}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        norm = key.replace("_", "-")
        spec = by_config_key.get(norm) or by_dest.get(norm.replace("-", "_"))
        if spec is None:
            # ignore unknown keys silently in shared files like pyproject.toml
            continue
        if isinstance(value, bool) and spec.kind != "bool":
            out[spec.dest] = coerce_value(spec, value)
        else:
            out[spec.dest] = coerce_value(spec, value)
    return out


def load_env_config(environ: dict[str, str] | None = None) -> dict[str, Any]:
    """Collect ``TN_VENV_*`` variables into a {dest: coerced_value} mapping."""
    environ = environ if environ is not None else dict(os.environ)
    out: dict[str, Any] = {}
    for spec in OPTION_SPECS.values():
        if spec.cli_only:
            continue
        if spec.env_name in environ:
            out[spec.dest] = coerce_value(spec, environ[spec.env_name])
    return out
