# Configuration files

This page is the normative reference for file-based configuration. For the
narrative explanation and examples, see {doc}`../guide/configuration`.

## Discovery algorithm

1. If `--config FILE` is given, use exactly that file (must exist).
2. Else if `TN_VENV_CONFIG_FILE` is set, use that file (must exist).
3. Else, starting at the current working directory and walking up parent
   by parent, test the candidates below in order within each directory.
   After testing a directory that contains a `.git` entry, stop walking.
4. The first candidate that *qualifies* becomes the config file. If none
   qualifies, no file layer is applied.

| Order | Candidate | Qualifying condition | Section read |
|---|---|---|---|
| 1 | `pyproject.toml` | has `[tool.tn-venv]` or `[tool.tn_venv]` | that table |
| 2 | `tn-venv.ini` | exists | `[tn-venv]`, `[tn_venv]`, or `[virtualenv]` |
| 3 | `tn_venv.ini` | exists | same as above |
| 4 | `.tn-venv.toml` | exists | TOML top level |
| 5 | `setup.cfg` | has `[tn_venv]` | `[tn_venv]` |

Malformed TOML/INI is a `ConfigError` (exit code 2). A `pyproject.toml`
*without* a tn-venv section is skipped — it never shadows a config file
higher up the tree.

## Key mapping

Config keys match long-option names with dashes, and are normalized before
lookup (`_` ≡ `-`, case preserved). Each key maps to the option of the same
name; CLI-only options (`list-pythons`, `dry-run`, `config`, `no-config`)
are not read from files.

| Key | Type | Example |
|---|---|---|
| `python` | list | `["3.12", "3.11"]` or `"3.12, 3.11"` |
| `clear` | bool | `true` |
| `upgrade` | bool | `false` |
| `system-site-packages` | bool | `false` |
| `symlinks` | bool | `true` |
| `copies` | bool | `false` |
| `scm-ignore` | `git` \| `none` | `"git"` |
| `seeder` | `pip` \| `none` | `"pip"` |
| `no-pip` | bool | `false` |
| `pip` | version string | `"24.0"` |
| `upgrade-pip` | bool | `true` |
| `setuptools` | bool or version | `true` / `"69.0.3"` |
| `wheel` | bool or version | `true` |
| `extra-search-dir` | list | `["/srv/wheels"]` |
| `offline` | bool | `false` |
| `with` / `seed-packages` | list | `["requests"]` |
| `requirements` | list | `["dev-requirements.txt"]` |
| `activators` | list or string | `"powershell,batch"` |
| `prompt` | string | `"my-project"` |
| `quiet` | integer | `0` |
| `verbose` | integer | `1` |
| `color` | bool | `true` |

Unknown keys are ignored, so shared files (notably `pyproject.toml`) may
contain other tools' sections without errors.

## Type coercion

TOML files provide native types; INI files provide strings and use the same
coercion as {ref}`environment variables <type-coercion>`.
A TOML boolean given to a version-typed option (`pip`, `setuptools`,
`wheel`) means "unpinned": `setuptools = true` ≡ `--setuptools`.

## Complete example

```toml
# pyproject.toml
[tool.tn-venv]
python = ["3.12", "3.11"]
prompt = "billing-api"
system-site-packages = false
symlinks = true                      # on Windows, falls back to copies if symlinking fails
scm-ignore = "git"
seeder = "pip"
upgrade-pip = true
setuptools = true
wheel = true
with = ["pip-tools"]
requirements = ["requirements.txt", "dev-requirements.txt"]
activators = "bash,powershell"
verbose = 0
```
