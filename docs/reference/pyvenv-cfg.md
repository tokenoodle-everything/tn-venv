# pyvenv.cfg reference

Every environment contains `pyvenv.cfg` at its root. CPython's site
machinery reads it at startup to detect the environment and locate the base
installation. `tn-venv` writes the standard keys plus a small set of
documented extensions; unknown keys are ignored by consumers.

## Example

```ini
home = C:\Python314
implementation = cpython
version_info = 3.14.7
include-system-site-packages = false
version = 3.14.7
prompt = 'my-project'
executable = C:\Python314\python.exe
base-executable = C:\Python314\python.exe
command = C:\Python314\python.exe -m tn_venv .venv --prompt my-project
tn-venv = your.release.version
```

## Standard keys

| Key | Meaning |
|---|---|
| `home` | directory containing the base interpreter's executable; the runtime resolves the stdlib from here |
| `include-system-site-packages` | `true` when created with `--system-site-packages` |
| `version` | `major.minor.micro` of the base interpreter |
| `prompt` | only written when `--prompt` was given; `repr()`-quoted, matching stdlib venv |
| `executable` | realpath of the base executable (stdlib venv writes this since 3.12) |

## Extension keys written by tn-venv

| Key | Meaning |
|---|---|
| `implementation` | `sys.implementation.name` of the base interpreter (`cpython`, `pypy`, …) |
| `version_info` | full `major.minor.micro` (mirrors virtualenv's key of the same name) |
| `base-executable` | path to `sys._base_executable` — the binary that was actually copied or linked |
| `command` | the full command line that created the environment, for forensics and reproduction |
| `tn-venv` | the version of tn-venv that created the environment |

```{note}
`home` points at the *directory* of the base executable, per PEP 405;
`executable` / `base-executable` point at the executable *file*. Tools that
parse `pyvenv.cfg` (including CPython itself) rely on `home` first, so
tn-venv never deviates from the standard there.
```
