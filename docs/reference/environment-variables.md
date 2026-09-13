# Environment variables

Every option that is not marked *CLI only* in {doc}`cli` has a
corresponding environment variable. Variables sit between CLI flags and
config files in {ref}`precedence <config-precedence>`.

## Naming rule

Take the option's destination name, uppercase it, and prefix with
`TN_VENV_`:

```text
--system-site-packages  →  TN_VENV_SYSTEM_SITE_PACKAGES
--with                  →  TN_VENV_SEED_PACKAGES   (exception, see table)
```

## Complete table

| Variable | Option | Type |
|---|---|---|
| `TN_VENV_PYTHON` | `-p/--python` | list (comma-separated) |
| `TN_VENV_CLEAR` | `--clear` | bool |
| `TN_VENV_UPGRADE` | `--upgrade` | bool |
| `TN_VENV_SYSTEM_SITE_PACKAGES` | `--system-site-packages` | bool |
| `TN_VENV_SYMLINKS` | `--symlinks` | bool |
| `TN_VENV_COPIES` | `--copies` | bool |
| `TN_VENV_SCM_IGNORE` | `--scm-ignore` | `git` \| `none` |
| `TN_VENV_SEEDER` | `--seeder` | `pip` \| `none` |
| `TN_VENV_NO_PIP` | `--no-pip` | bool |
| `TN_VENV_PIP` | `--pip` | version string |
| `TN_VENV_UPGRADE_PIP` | `--upgrade-pip` | bool |
| `TN_VENV_SETUPTOOLS` | `--setuptools` | bool or version |
| `TN_VENV_WHEEL` | `--wheel` | bool or version |
| `TN_VENV_EXTRA_SEARCH_DIR` | `--extra-search-dir` | list (comma-separated) |
| `TN_VENV_OFFLINE` | `--offline` | bool |
| `TN_VENV_SEED_PACKAGES` | `--with/--seed-package` | list (comma-separated) |
| `TN_VENV_REQUIREMENTS` | `-r/--requirements` | list (comma-separated) |
| `TN_VENV_ACTIVATORS` | `--activators` | list (comma-separated) |
| `TN_VENV_PROMPT` | `--prompt` | string |
| `TN_VENV_QUIET` | `-q/--quiet` | integer |
| `TN_VENV_VERBOSE` | `-v/--verbose` | integer |
| `TN_VENV_COLOR` | `--color/--no-color` | bool |

## Additional variables

These are not option mappings but are honored by the reporter and the
configuration loader:

| Variable | Effect |
|---|---|
| `TN_VENV_CONFIG_FILE` | explicit config file path (equivalent of `--config`) |
| `TN_VENV_FORCE_COLOR` | force colored output even when stdout is not a TTY |
| `NO_COLOR` | disable colored output ([no-color.org](https://no-color.org/) convention) |
| `FORCE_COLOR` | force colored output (common convention) |
| `UV_PYTHON_INSTALL_DIR` | extra root scanned by the `uv` discovery provider |
| `PYENV_ROOT` | root scanned by the `pyenv` discovery provider |

(type-coercion)=
## Type coercion

- **bool** — case-insensitive `1`, `true`, `yes`, `on`, `y`, `t` are true;
  `0`, `false`, `no`, `off`, `n`, `f`, and the empty string are false.
  Anything else is a configuration error (exit code 2).
- **list** — comma-separated; whitespace around items is stripped; empty
  items are dropped.
- **integer** — parsed with `int()`; invalid values are configuration
  errors.
- **string** — used verbatim.
