# tn-venv

> Create a Python virtual environment — **batteries included**.

`tn-venv` is a zero-dependency, batteries-included replacement for `python -m venv`
that picks sensible defaults out of the box: running bare `tn-venv` creates `./.venv`
with the current interpreter and `pip` already installed.

```bash
$ tn-venv
==> creating virtual environment at ./.venv
==> installing pip (ensurepip)
interpreter: cpython 3.14.7 (64-bit) from C:\Python314\python.exe
==> python binaries installed to ./.venv\Scripts
environment ready: .\.venv\Scripts\python.exe
activate with: .\.venv\Scripts\Activate.ps1  (PowerShell)  |  .\.venv\Scripts\activate.bat  (cmd)
```

---

## Why tn-venv?

| | `tn-venv` | stdlib `venv` | `virtualenv` |
|---|---|---|---|
| Zero runtime dependencies | ✅ | ✅ | ❌ |
| Ships `pip`, `setuptools`, `wheel` after creation | ✅ | ❌ (3.12+) | ✅ |
| Generates activation scripts for **bash / zsh / fish / csh / Nushell / PowerShell / cmd** | ✅ | bash + PowerShell | 5 shells |
| Discovers interpreters from PATH, registry, `py` launcher, `uv`, `pyenv` | ✅ | ❌ | partial |
| Pin or upgrade pip from the index | ✅ | ❌ | ✅ |
| Offline mode / extra wheel dirs | ✅ | ❌ | ✅ |
| Pure-Python, no compiled extensions | ✅ | ✅ | ❌ |
| Ships `activate_this.py` | ✅ | ❌ | ✅ |
| Locking against concurrent creation | ✅ | ❌ | ❌ |
| One command, sensible defaults | ✅ | ❌ | ✅ |

Requires **Python 3.11+**.

---

## Installation

```bash
pip install tn-venv
```

Or directly from the repo:

```bash
pip install git+https://github.com/tokenoodle-everything/tn-venv.git
```

This installs two console scripts:

- `tn-venv`
- `tn_venv` (alias)

You can also invoke the CLI without installing anything:

```bash
python -m tn_venv .venv
```

---

## Quick start
```bash
tn-venv --list-pythons

# Print the resolved configuration without creating anything
tn-venv --dry-run
```

---

## CLI reference

### Interpreter selection

| Flag | Description |
|---|---|
| `-p SPEC` / `--python SPEC` | Python to build from — a path, a version (`3`, `3.12`, `3.12.1`), a name (`python3.12`, `pypy3.10`) or a PEP 514-ish tag. Repeatable; first match wins. Default: the interpreter running `tn-venv`. |
| `--list-pythons` | List every discoverable interpreter and exit. |

### Creator options

| Flag | Description |
|---|---|
| `--clear` | Delete the destination directory before creating. |
| `--upgrade` | Upgrade an existing environment in place (keep installed packages). |
| `--system-site-packages` | Give the environment access to the system site-packages. |
| `--symlinks` / `--no-symlinks` | Symlink the interpreter binaries (default on POSIX). |
| `--copies` / `--no-copies` | Copy the interpreter binaries (default on Windows). |
| `--scm-ignore {git,none}` | Write a source-control ignore file (default: `git`). |

### Seeder options

| Flag | Description |
|---|---|
| `--seeder {pip,none}` | Package installer to seed the environment with (default: `pip`). |
| `--no-pip` / `--without-pip` | Skip pip installation. |
| `--pip [VERSION]` | Pip version to install. Omit value for the latest release (`--pip` ≡ `--pip latest`), pass a version to pin (`--pip 24.0`). |
| `--upgrade-pip` | Upgrade pip to the latest release from the package index. |
| `--setuptools [VERSION]` | Install setuptools (optionally pinned). Not bundled on Python ≥ 3.12. |
| `--wheel [VERSION]` | Install wheel (optionally pinned). |
| `--extra-search-dir DIR` | Additional directory to search for wheels/sdists (`PIP_FIND_LINKS`). Repeatable. |
| `--offline` | Don't reach the network; use only bundled wheels and `--extra-search-dir` (`PIP_NO_INDEX`). |
| `--with PKG` / `--seed-package PKG` | Install extra packages after seeding. Repeatable. |
| `-r FILE` / `--requirements FILE` | Install from a requirements file. Repeatable. |

### Activation options

| Flag | Description |
|---|---|
| `--activators NAMES` | Comma-separated activation scripts to generate. Names: `bash`, `batch`, `powershell`, `fish`, `csh`, `nushell`, `python`, plus `all` and `default`. Prefix with `-` to exclude (e.g. `-fish`). |
| `--prompt NAME` | Custom prompt shown when the environment is active (default: the environment folder name). |

### Miscellaneous

| Flag | Description |
|---|---|
| `-q` / `--quiet` | Reduce verbosity (repeatable). |
| `-v` / `--verbose` | Increase verbosity (repeatable). |
| `--color` / `--no-color` | Force colored output on or off. Honors `NO_COLOR` and `FORCE_COLOR`. |
| `--dry-run` | Print the resolved configuration without creating anything. |
| `--config FILE` | Explicit path to a config file (overrides discovery). |
| `--no-config` | Ignore config files and environment variables. |
| `--version` | Print `tn-venv` version and exit. |
| `-h` / `--help` | Show help and exit. |

---

```bash
# One command: create ./.venv with pip and the current interpreter
tn-venv

# Pick a destination and a specific interpreter version
tn-venv .venv -p 3.12

# Let the environment see globally-installed packages
tn-venv /tmp/x --system-site-packages
```

## Configuration

Configuration precedence (highest first):

1. **CLI flags** — e.g. `tn-venv --clear`
2. **`TN_VENV_*` environment variables** — e.g. `TN_VENV_CLEAR=1`
3. **Config file** — discovered automatically, or via `--config FILE` / `TN_VENV_CONFIG_FILE`
4. **Built-in defaults**

### Config file discovery

`tn-venv` walks the current directory and its parents (stopping at `.git`) looking for the first match:

1. `pyproject.toml` — only counts when it contains a `[tool.tn-venv]` or `[tool.tn_venv]` section
2. `tn-venv.ini`
3. `tn_venv.ini`
4. `.tn-venv.toml` — top-level keys
5. `setup.cfg` — only when it has a `[tn_venv]` section

### `pyproject.toml`

```toml
[tool.tn-venv]
python = ["3.12"]
prompt = "my-project"
system-site-packages = false
activators = "powershell,batch,-nushell"
with = ["requests", "click"]
upgrade-pip = true
```

### `tn-venv.ini`

```ini
[tn-venv]
python = 3.12, 3.13
prompt = my-project
clear = yes
extra-search-dir = /srv/wheels
requirements = dev-requirements.txt
```

### Environment variables

Every option has a `TN_VENV_<NAME>` env var (uppercased destination):

```bash
export TN_VENV_PYTHON=3.12
export TN_VENV_PROMPT=my-project
export TN_VENV_CLEAR=1
export TN_VENV_NO_PIP=0
export TN_VENV_ACTIVATORS=powershell,batch
```

## Python API

Use `tn_venv.create_venv` programmatically:

```python
from tn_venv import create_venv

result = create_venv(
    ".venv",
    python="3.12",
    with_pip=True,
    pip="24.0",
    setuptools=True,
    wheel=True,
    packages=["requests", "click"],
    requirements=["dev-requirements.txt"],
    activators=["bash", "powershell"],
    prompt="my-project",
    quiet=True,
)

print(result.env_dir)        # PosixPath('.venv')
print(result.exe)            # PosixPath('.venv/bin/python')
print(result.bin_path)       # PosixPath('.venv/bin')
print(result.site_packages)  # PosixPath('.venv/lib/python3.12/site-packages')
print(result.prompt)         # 'my-project'
print(result.activation_scripts)
print(result.seed.pip)       # '24.0'
```
