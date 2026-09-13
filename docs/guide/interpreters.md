# Choosing an interpreter

By default, `tn-venv` builds the environment from the interpreter that is
running `tn-venv` itself. The `-p` / `--python` option overrides that, and
accepts four different kinds of *spec*.

## Spec grammar

| Form | Examples | Meaning |
|---|---|---|
| path | `C:\Python311\python.exe`, `./bin/python3` | probe this exact executable |
| version | `3`, `3.12`, `3.12.1` | any discoverable interpreter matching the version |
| command name | `python3.12`, `pypy3.10` | resolved on `PATH`, then matched as a version |
| implementation + version | `pypy3.10`, `cpython-3.12` | restrict by implementation |

The formal grammar is:

```text
spec      := [implementation] version ["-" arch]
implementation := "cpython" | "pypy" | "graalpy" | "python" | "py"
version   := major ["." minor ["." patch]]
arch      := "32" | "64"
```

Matching is prefix-based: `-p 3` accepts any Python 3, `-p 3.12` accepts any
3.12.x, and `-p 3.12.1` demands exactly 3.12.1. `python3.12` and plain
`3.12` both imply CPython.

The option is **repeatable**, and the first satisfiable spec wins:

```console
$ tn-venv -p 3.13 -p 3.12 -p 3.11
```

## Discovery providers

When a spec is not a path, `tn-venv` enumerates candidate interpreters from
six providers, in this order:

| Provider | Source | Platforms |
|---|---|---|
| `current` | the interpreter running `tn-venv` | all |
| `PATH` | `python`, `python3`, `python3.x`, … found by `PATH` lookup | all |
| `registry` | PEP 514 registry keys under `HKCU\Software\Python` and `HKLM\Software\Python` | Windows |
| `py-launcher` | `py -0p` (the PEP 397 launcher) | Windows |
| `uv` | `uv`'s managed installs (`UV_PYTHON_INSTALL_DIR`, platform data dir) | all |
| `pyenv` | `PYENV_ROOT/versions`, `~/.pyenv/versions` | all |

Candidates are de-duplicated by resolved executable path, and a provider
that fails (for example, `py` not installed) is skipped silently. Among the
matching candidates, `tn-venv` picks the **highest version**, preferring the
currently running interpreter on ties.

(registry-provider)=
### The Windows registry provider (PEP 514)

On Windows, interpreters may register themselves under
`Software\Python\<Company>\<Tag>` in either `HKEY_CURRENT_USER` or
`HKEY_LOCAL_MACHINE`. `tn-venv` reads the `ExecutablePath` value of the
`InstallPath` subkey, falling back to `<InstallPath>\python.exe`. This is
how the official python.org installers, the NuGet distribution, and most
enterprise deployments advertise themselves.

## Probing

Every candidate is *probed* by executing it with a small embedded script
that prints a JSON description of itself (version, prefixes, architecture,
whether the GIL is disabled, where its `venv` launcher binaries live, and
so on). Probing is isolated (`-I`), bounded by a 30-second timeout, and
cached for the lifetime of the process, so a dozen candidates cost very
little.

An executable that exists but cannot be executed — wrong architecture,
missing runtime, permission problem — is reported as unusable and skipped
during spec matching, with the reason shown at `-vv`:

```console
$ tn-venv -p 3.12 -vv
debug: probing interpreter path C:\Python312\python.exe
...
```

## Listing everything tn-venv can see

```console
$ tn-venv --list-pythons
==> discovering interpreters…
  3.14.7 (64-bit)  C:\Python314\python.exe                        — current
  3.14.7 (64-bit)  C:\Users\me\AppData\Roaming\uv\python\...\python.exe  — uv:cpython-3.14.7
  3.12.8 (64-bit)  C:\Python312\python.exe                        — registry:HKCU/PythonCore/3.12
```

Each row shows the probed version and bitness, the executable path, a
`[free-threaded]` marker where applicable, and the provider that supplied
the candidate.

## Errors

When no candidate satisfies any spec, the command fails with exit code 1
and an `InterpreterNotFoundError` message listing every candidate that was
probed:

```text
error: no Python interpreter found for spec '9.99'
candidates probed:
  C:\Python314\python.exe (...)
```

```{tip}
If discovery picks a different interpreter than you expect, run
`tn-venv --list-pythons` and pass the exact path with `-p`.
```
