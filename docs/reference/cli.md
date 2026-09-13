# CLI reference

```text
tn-venv [OPTIONS] [DEST]
```

`DEST` is the environment directory. It defaults to `.venv`, so bare
`tn-venv` is a complete command. Exit codes are documented in
{doc}`exit-codes`.

## Interpreter

### `-p SPEC`, `--python SPEC`

Interpreter to build from. `SPEC` may be a filesystem path, a version
(`3`, `3.12`, `3.12.1`), a command name (`python3.12`), or an
implementation-qualified version (`pypy3.10`, `cpython-3.12-64`).
Repeatable; the first satisfiable spec wins. Default: the interpreter
running tn-venv. See {doc}`../guide/interpreters`.

Environment: `TN_VENV_PYTHON` (comma-separated). Config key: `python`.

### `--list-pythons`

Probe and print every discoverable interpreter, then exit. CLI only.

## Creator

### `--clear`

Delete `DEST` entirely before creating. Read-only files are handled.
Environment: `TN_VENV_CLEAR`. Config key: `clear`.

### `--upgrade`

Upgrade an existing environment in place: refresh binaries, `pyvenv.cfg`,
activation scripts, and pip; keep `site-packages`. Creating a missing
destination with `--upgrade` simply creates it.
Environment: `TN_VENV_UPGRADE`. Config key: `upgrade`.

### `--system-site-packages` / `--no-system-site-packages`

Give the environment access to the base installation's site-packages
(default: isolated). Recorded as `include-system-site-packages` in
`pyvenv.cfg`. Environment: `TN_VENV_SYSTEM_SITE_PACKAGES`. Config key:
`system-site-packages`.

### `--symlinks` / `--no-symlinks`

Symlink interpreter binaries instead of copying them. Default on POSIX.
On Windows, symlinking requires Developer Mode or elevation; failure falls
back to copies with a warning.
Environment: `TN_VENV_SYMLINKS`. Config key: `symlinks`.

### `--copies` / `--no-copies`

Copy interpreter binaries instead of symlinking them. Default on Windows.
Passing both `--symlinks` and `--copies` is a configuration error
(exit code 2). Environment: `TN_VENV_COPIES`. Config key: `copies`.

### `--scm-ignore {git,none}`

Write a source-control ignore file into the environment. `git` (the
default) writes a `.gitignore` containing `*`. `none` writes nothing.
Environment: `TN_VENV_SCM_IGNORE`. Config key: `scm-ignore`.

## Seeder

### `--seeder {pip,none}`

Which installer to seed with. Default: `pip`.
Environment: `TN_VENV_SEEDER`. Config key: `seeder`.

### `--no-pip`, `--without-pip`

Skip seeding entirely; equivalent to `--seeder none` and takes precedence
over it. Environment: `TN_VENV_NO_PIP`. Config key: `no-pip`.

### `--pip [VERSION]`

Pip version to install. With no value, installs the latest release
(equivalent to `latest`). With a value, pins `pip==VERSION`. The special
value `bundled` keeps the `ensurepip`-provided version (the default).
Environment: `TN_VENV_PIP`. Config key: `pip`.

### `--upgrade-pip` / `--no-upgrade-pip`

Upgrade pip to the latest release from the index after `ensurepip`.
Takes precedence over `--pip VERSION`.
Environment: `TN_VENV_UPGRADE_PIP`. Config key: `upgrade-pip`.

### `--setuptools [VERSION]`

Install setuptools — unpinned with no value, or `setuptools==VERSION`.
Not bundled by `ensurepip` on Python ≥ 3.12.
Environment: `TN_VENV_SETUPTOOLS`. Config key: `setuptools`.

### `--wheel [VERSION]`

Install wheel — unpinned with no value, or `wheel==VERSION`.
Environment: `TN_VENV_WHEEL`. Config key: `wheel`.

### `--extra-search-dir DIR`

Additional directory of wheels/sdists for pip to search
(`PIP_FIND_LINKS`). Repeatable.
Environment: `TN_VENV_EXTRA_SEARCH_DIR` (comma-separated).
Config key: `extra-search-dir`.

### `--offline` / `--no-offline`

Never reach the network: sets `PIP_NO_INDEX=1` for all pip invocations.
Environment: `TN_VENV_OFFLINE`. Config key: `offline`.

### `--with PKG`, `--seed-package PKG`

Install `PKG` into the environment after seeding. Any pip requirement
specifier is accepted. Repeatable.
Environment: `TN_VENV_SEED_PACKAGES` (comma-separated).
Config key: `with` / `seed-packages`.

### `-r FILE`, `--requirements FILE`

Install from a pip requirements file after seeding. Repeatable; a missing
file is a `SeedError` (exit code 1).
Environment: `TN_VENV_REQUIREMENTS` (comma-separated).
Config key: `requirements`.

## Activation

### `--activators LIST`

Comma-separated activation scripts to generate: `bash`, `batch`,
`powershell`, `fish`, `csh`, `nushell`, `python`, plus pseudo-names `all`
and `default`; prefix a name with `-` to exclude it from the default set.
Repeatable. Default: everything supported on the host platform.
Environment: `TN_VENV_ACTIVATORS`. Config key: `activators`.

### `--prompt TEXT`

Prompt string shown while the environment is active. Default: the
environment folder name. A custom prompt is recorded in `pyvenv.cfg`.
Environment: `TN_VENV_PROMPT`. Config key: `prompt`.

## Behaviour

### `-q`, `--quiet`

Decrease verbosity; repeatable. `-q` shows errors only.
Environment: `TN_VENV_QUIET` (integer). Config key: `quiet`.

### `-v`, `--verbose`

Increase verbosity; repeatable. `-v` adds per-step detail, `-vv` echoes
every subprocess and its output.
Environment: `TN_VENV_VERBOSE` (integer). Config key: `verbose`.

### `--color` / `--no-color`

Force colored output on or off. Default: auto-detect (TTY,
`NO_COLOR`/`FORCE_COLOR` honored, VT processing enabled on Windows).
Environment: `TN_VENV_COLOR`, `TN_VENV_FORCE_COLOR`. Config key: `color`.

### `--dry-run`

Print the fully resolved configuration and exit without creating anything.
CLI only.

### `--config FILE`

Use this config file instead of discovering one.
CLI only; the env-var equivalent is `TN_VENV_CONFIG_FILE`.

### `--no-config`

Ignore all config files and `TN_VENV_*` environment variables. CLI only.

### `--version`

Print the tn-venv version and exit.

### `-h`, `--help`

Print help and exit.
