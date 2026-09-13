# Activation

Activation puts the environment's binary directory at the front of `PATH`
and records the environment in `VIRTUAL_ENV`, so `python` and `pip` resolve
to the environment without any absolute paths. `tn-venv` generates scripts
for **seven** activation mechanisms in one pass.

## Generated scripts

| File | Shell | Activation command |
|---|---|---|
| `activate` | bash, zsh, and other POSIX sh | `source <env>/bin/activate` |
| `activate.bat` | cmd.exe | `<env>\Scripts\activate.bat` |
| `deactivate.bat` | cmd.exe | `deactivate.bat` |
| `Activate.ps1` | PowerShell / pwsh | `<env>\Scripts\Activate.ps1` |
| `activate.fish` | fish | `source <env>/bin/activate.fish` |
| `activate.csh` | csh, tcsh | `source <env>/bin/activate.csh` |
| `activate.nu` | Nushell | `overlay use <env>/bin/activate.nu` |
| `activate_this.py` | *no shell — in-process* | see below |

On Windows the environment directory is `Scripts`; elsewhere it is `bin`.
`activate.bat` and `deactivate.bat` are only generated on Windows; every
other script is generated on every platform.

All scripts share the same semantics:

1. `VIRTUAL_ENV` is set to the environment directory and exported.
2. The environment's binary directory is prepended to `PATH`; the previous
   value is stashed so `deactivate` can restore it exactly.
3. `PYTHONHOME` is unset if set (and restored by `deactivate`).
4. Unless `VIRTUAL_ENV_DISABLE_PROMPT` is non-empty, the shell prompt is
   prefixed with `(<prompt>) ` and `VIRTUAL_ENV_PROMPT` is set.
5. `deactivate` (a shell function, or `deactivate.bat` on cmd) reverses all
   of the above, including restoring the previous prompt.

Nested activation is safe: activating environment B while A is active
stacks the changes, and `deactivate` returns to A's state.

## Choosing which scripts to generate

```console
$ tn-venv .venv --activators powershell,batch
$ tn-venv .venv --activators all
$ tn-venv .venv --activators default,-nushell,-csh
```

The value is comma-separated and repeatable. Accepted names are `bash`,
`batch`, `powershell`, `fish`, `csh`, `nushell`, `python`, plus the two
pseudo-names `all` and `default`. A leading `-` removes a name from the
default set. Unknown names are rejected with exit code 2 and the list of
valid names.

## The prompt

By default the prompt is the environment's folder name. Override it with:

```console
$ tn-venv .venv --prompt "api-dev"
```

A custom prompt is also recorded in `pyvenv.cfg` (see
{doc}`../reference/pyvenv-cfg`), which is how `python -m venv --upgrade`
learns to keep it. To suppress prompt modification at activation time,
without changing the scripts, set `VIRTUAL_ENV_DISABLE_PROMPT` to any
non-empty value before sourcing.

## activate_this.py

`activate_this.py` activates an environment **inside an already-running
Python process** — the classic `virtualenv` mechanism, kept for
compatibility with embedding tools and long-lived application servers:

```python
activate_this = "/path/to/.venv/bin/activate_this.py"
with open(activate_this) as f:
    code = compile(f.read(), activate_this, "exec")
    exec(code, {"__file__": activate_this})
```

It prepends the environment's binary directory to `PATH`, sets
`VIRTUAL_ENV` and `VIRTUAL_ENV_PROMPT`, adds the environment's
`site-packages` via `site.addsitedir()`, and rewrites `sys.prefix` (keeping
the old value in `sys.real_prefix`). It cannot un-import already-loaded
modules, so it is only safe to use early in a process's lifetime.

```{warning}
On POSIX systems the POSIX-shell script must be *sourced*, not executed:
`source .venv/bin/activate`. Executing it in a subshell activates the
subshell only and is silently useless — the scripts detect nothing; this is
inherent to how shells work, not a tn-venv limitation.
```
