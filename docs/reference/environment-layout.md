# Environment layout

The files and directories `tn-venv` writes into `DEST`, per platform. The
layout follows PEP 405 and matches `python -m venv`.

## Windows

```text
.venv/
├── pyvenv.cfg              # environment configuration (see pyvenv-cfg)
├── .gitignore              # unless --scm-ignore none
├── Include/                # PEP 405 include directory
├── Lib/
│   └── site-packages/      # where pip installs into
└── Scripts/
    ├── python.exe          # venvlauncher.exe redirector (Python ≥ 3.11)
    ├── pythonw.exe         # venvwlauncher.exe (windowed)
    ├── activate            # bash / zsh (Git Bash, MSYS2, Cygwin)
    ├── activate.bat        # cmd.exe
    ├── deactivate.bat      # cmd.exe
    ├── Activate.ps1        # PowerShell / pwsh
    ├── activate.fish       # fish
    ├── activate.csh        # csh / tcsh
    ├── activate.nu         # Nushell
    ├── activate_this.py    # in-process activation
    ├── pip.exe             # ┐
    ├── pip3.exe            # ├ installed by the seeder
    └── pip3.14.exe         # ┘
```

### Where the binaries come from

| Mode | `python.exe` | Runtime DLLs |
|---|---|---|
| copies (default), Python ≥ 3.11 | copy of the base install's `venvlauncher.exe`, which redirects through `pyvenv.cfg` | resolved from the base install at runtime |
| copies, Python ≤ 3.10 (or no launchers) | copy of the real `python.exe` | `python3*.dll`, `vcruntime*.dll` copied alongside |
| `--symlinks` | symlink to the real `python.exe` | all `python*`/`vcruntime*` DLLs symlinked too |

Symlink mode that fails (no Developer Mode privilege) falls back to copies
with a warning. Free-threaded (`3.13t`) and debug (`_d`) builds use their
matching launcher names.

## POSIX (Linux, macOS, …)

```text
.venv/
├── pyvenv.cfg
├── .gitignore
├── include/
├── lib/
│   └── python3.14/
│       └── site-packages/
├── lib64 -> lib            # 64-bit POSIX, except macOS
└── bin/
    ├── python3             # symlink (default) or copy of the base binary
    ├── python              # ┐ relative links to python3
    ├── python3.14          # ┘
    ├── activate
    ├── Activate.ps1
    ├── activate.fish
    ├── activate.csh
    ├── activate.nu
    ├── activate_this.py
    └── pip, pip3, pip3.14  # installed by the seeder
```

On POSIX, symlinks are the default; `--copies` copies the binary and marks
it executable. PyPy environments get a `pypy3` alias in addition.

## What is *not* written

- No files outside `DEST` except the transient `DEST.tn-venv.lock` lock
  file, which is removed on completion.
- No state directories, no caches: `tn-venv` keeps nothing between runs,
  so two invocations never observe each other except through the
  destination itself.
