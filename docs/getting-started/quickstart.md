# Quick start

This page walks through the most common workflows in five minutes. Every
command shown here is safe to re-run.

## Your first environment

```console
$ tn-venv
```

That single command:

1. resolves the interpreter running `tn-venv` as the base interpreter;
2. creates `./.venv` with the platform's standard layout
   (`Scripts\` on Windows, `bin/` elsewhere);
3. writes `pyvenv.cfg` recording the interpreter's home and version;
4. generates activation scripts for bash, cmd, PowerShell, fish, csh,
   Nushell, and the legacy `activate_this.py`;
5. installs `pip` into the environment via `ensurepip`;
6. writes a `.gitignore` containing `*` so the environment is never
   committed by accident.

A different destination is given positionally:

```console
$ tn-venv .envs/dev
```

## Choosing an interpreter

```console
$ tn-venv -p 3.12            # highest installed 3.12.x
$ tn-venv -p 3.11 -p 3.10    # try 3.11, fall back to 3.10
$ tn-venv -p C:\Python311\python.exe
$ tn-venv -p pypy3.10
```

See {doc}`../guide/interpreters` for the full spec grammar and discovery
order. To preview what would happen without creating anything:

```console
$ tn-venv --dry-run
==> resolved configuration (dry run — nothing created)
  dest                     = WindowsPath('.venv')
  ...
```

## Activating

::::{tab-set}

:::{tab-item} PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
```
:::

:::{tab-item} cmd.exe
```bat
.\.venv\Scripts\activate.bat
```
:::

:::{tab-item} bash / zsh
```bash
source .venv/Scripts/activate    # Windows (Git Bash)
source .venv/bin/activate        # POSIX
```
:::

:::{tab-item} fish
```fish
source .venv/bin/activate.fish
```
:::

:::{tab-item} Nushell
```text
overlay use .venv/bin/activate.nu
```
:::
::::

`deactivate` (or `deactivate.bat` on cmd) returns the shell to its previous
state. Activation is covered in depth in {doc}`../guide/activation`.

## Installing packages at creation time

```console
$ tn-venv .venv --with requests --with click==8.1
$ tn-venv .venv -r requirements.txt -r dev-requirements.txt
$ tn-venv .venv --setuptools --wheel --upgrade-pip
```

Everything about package seeding — including fully offline environments —
is documented in {doc}`../guide/seeding`.

## Housekeeping

```console
$ tn-venv .venv --upgrade    # refresh binaries in place, keep packages
$ tn-venv .venv --clear      # delete the directory and start over
```

The difference between the two, and the lock that guards concurrent runs,
is explained in {doc}`../guide/lifecycle`.

## Asking for help

```console
$ tn-venv --help             # full option summary
$ tn-venv --version          # print version and exit
$ tn-venv --list-pythons     # every interpreter tn-venv can find
```
