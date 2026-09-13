# tn-venv

**Create Python virtual environments with one command — batteries included.**

`tn-venv` is a zero-dependency, batteries-included replacement for
`python -m venv` that picks rigorous, predictable defaults: running bare
`tn-venv` creates `./.venv` from the current interpreter, installs `pip`,
writes activation scripts for every major shell, and records exactly how the
environment was made.

```console
$ tn-venv
==> creating virtual environment at ./.venv
interpreter: cpython 3.14.7 (64-bit) from C:\Python314\python.exe
==> installing pip (ensurepip)
==> environment ready: .\.venv\Scripts\python.exe
```

## Feature tour

:::::{grid} 1 1 2 2
:gutter: 3

::::{grid-item-card} One command
Running bare `tn-venv` creates `./.venv` with the current interpreter and
`pip` pre-installed. No flags required — every knob has a defensible default.
::::

::::{grid-item-card} Interpreter discovery
`-p` accepts a path, a version (`3.12`), a command name (`python3.12`), or an
implementation (`pypy3.10`). Interpreters are located via `PATH`, the
{ref}`Windows registry <registry-provider>`,
the `py` launcher, `uv`, and `pyenv`.
::::

::::{grid-item-card} Real seeding
`pip` is installed through `ensurepip`; it can then be pinned
(`--pip 24.0`), upgraded (`--upgrade-pip`), or joined by `setuptools`,
`wheel`, extra packages (`--with`), and requirement files (`-r`).
::::

::::{grid-item-card} Every shell
Activation scripts are generated for **bash/zsh**, **cmd.exe**,
**PowerShell**, **fish**, **csh/tcsh**, **Nushell**, and the legacy
**activate_this.py** — all in one pass.
::::

::::{grid-item-card} Layered configuration
Every option is settable from the CLI, from `TN_VENV_*` environment
variables, or from `pyproject.toml` / `tn-venv.ini`, with documented
{ref}`precedence <config-precedence>`.
::::

::::{grid-item-card} Safe by construction
Creation runs under an {ref}`inter-process lock <concurrency-locking>`,
fails cleanly on existing environments, and never touches the network unless
you ask it to (`--offline`).
::::
:::::

## Where to next

| I want to… | Read |
|---|---|
| Install and create my first environment | {doc}`getting-started/installation`, {doc}`getting-started/quickstart` |
| Understand every CLI flag | {doc}`reference/cli` |
| Configure defaults per project | {doc}`guide/configuration` |
| Pick a specific Python | {doc}`guide/interpreters` |
| Seed packages offline | {doc}`guide/seeding` |
| Embed tn-venv in Python code | {doc}`guide/api` |
| Compare with venv / virtualenv / uv | {doc}`guide/comparison` |
| Hack on tn-venv itself | {doc}`development/architecture` |

```{toctree}
:maxdepth: 2
:caption: Getting started
:hidden:

getting-started/installation
getting-started/quickstart
```

```{toctree}
:maxdepth: 2
:caption: User guide
:hidden:

guide/interpreters
guide/lifecycle
guide/seeding
guide/activation
guide/configuration
guide/api
guide/comparison
guide/faq
```

```{toctree}
:maxdepth: 2
:caption: Reference
:hidden:

reference/cli
reference/environment-variables
reference/configuration-files
reference/environment-layout
reference/pyvenv-cfg
reference/python-api
reference/exit-codes
```

```{toctree}
:maxdepth: 2
:caption: Development
:hidden:

development/architecture
development/extending
development/testing
development/contributing
development/security
changelog
```
