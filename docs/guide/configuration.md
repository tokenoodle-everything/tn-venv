# Configuration

Every `tn-venv` option can be supplied in three ways, and the resolution
order is fixed and documented.

(config-precedence)=
## Precedence

From highest to lowest:

1. **Command-line flags** — `tn-venv --clear`
2. **Environment variables** — `TN_VENV_CLEAR=1`
3. **Config file** — discovered automatically, or named explicitly with
   `--config FILE` / `TN_VENV_CONFIG_FILE`
4. **Built-in defaults**

A layer only overrides lower layers when it actually supplies a value:
passing nothing on the CLI never masks an environment variable. Repeatable
options (`--python`, `--with`, …) are **replaced**, not appended, by a
higher layer.

`--no-config` disables layers 2 and 3 entirely.

## Config file discovery

Unless `--config` or `TN_VENV_CONFIG_FILE` names a file explicitly,
`tn-venv` walks from the current directory upward, stopping after the first
directory that contains a `.git` entry, and uses the first of these that
qualifies:

| Candidate | Qualifies when |
|---|---|
| `pyproject.toml` | it contains a `[tool.tn-venv]` or `[tool.tn_venv]` section |
| `tn-venv.ini` | always (its sections are read directly) |
| `tn_venv.ini` | always |
| `.tn-venv.toml` | always; options live at the TOML top level |
| `setup.cfg` | it contains a `[tn_venv]` section |

Unknown keys inside these files are **ignored**, so a shared
`pyproject.toml` can carry sections for other tools without conflict.

## pyproject.toml

```toml
[tool.tn-venv]
python = ["3.12", "3.11"]        # first satisfiable wins
prompt = "my-project"
system-site-packages = false
activators = "powershell,batch"
with = ["requests", "click"]
upgrade-pip = true
```

Keys are written kebab-case or snake_case; TOML native types (`bool`,
`str`, arrays) are accepted as-is.

## tn-venv.ini

```ini
[tn-venv]
python = 3.12, 3.13
prompt = my-project
clear = yes
extra-search-dir = /srv/wheels, /srv/sdists
requirements = dev-requirements.txt
```

INI values are strings; repeatable options take comma-separated values, and
booleans accept `1/0`, `true/false`, `yes/no`, `on/off` (case-insensitive).
An empty string is false. As a courtesy to migrated projects, a
`[virtualenv]` section is also read.

## Environment variables

Every non-CLI-only option maps to `TN_VENV_<NAME>` — the option's
destination uppercased. The full table is in
{doc}`../reference/environment-variables`; the rules of thumb:

```bash
export TN_VENV_PYTHON=3.12            # --python 3.12
export TN_VENV_SEED_PACKAGES=requests # --with requests
export TN_VENV_ACTIVATORS=powershell,batch
export TN_VENV_CLEAR=1                # booleans: 1/0, true/false, yes/no, on/off
export TN_VENV_VERBOSE=2              # counts accept an integer
```

`TN_VENV_CONFIG_FILE` names an explicit config file, and
`TN_VENV_FORCE_COLOR` forces colored output; both exist in addition to the
option mapping.

## Inspecting the resolved configuration

`--dry-run` prints the fully merged result and creates nothing:

```console
$ TN_VENV_PROMPT=demo tn-venv --dry-run
==> resolved configuration (dry run — nothing created)
  dest                     = WindowsPath('=demo')
  python                   = []
  clear                    = False
  upgrade                  = False
  system_site_packages     = False
  symlinks                 = None
  copies                   = None
  scm_ignore               = 'git'
  seeder                   = 'pip'
  no_pip                   = False
  pip                      = None
  upgrade_pip              = False
  setuptools               = None
  wheel                    = None
  extra_search_dir         = []
  offline                  = False
  seed_packages            = []
  requirements             = []
  activators               = []
  prompt                   = None
  quiet                    = 0
  verbose                  = 0
  color                    = None
  command                  = 'python.exe -m tn_venv --dry-run =demo'
```

This is the authoritative way to answer "why is my prompt `demo`?" — work
down the precedence list until you find the layer that set it.
