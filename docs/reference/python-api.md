# Python API reference

The public surface of the `tn_venv` package. Everything listed here is
covered by backward-compatibility commitments; anything not listed here is
internal.

## `tn_venv.create_venv`

```python
def create_venv(
    dest: str | os.PathLike = ".venv",
    *,
    python: str | list[str] | None = None,
    clear: bool = False,
    upgrade: bool = False,
    system_site_packages: bool = False,
    symlinks: bool | None = None,
    copies: bool | None = None,
    with_pip: bool = True,
    pip: str | None = None,
    setuptools: bool | str = False,
    wheel: bool | str = False,
    upgrade_pip: bool = False,
    packages: list[str] | None = None,
    requirements: list[str] | None = None,
    activators: list[str] | None = None,
    prompt: str | None = None,
    offline: bool = False,
    extra_search_dir: list[str] | None = None,
    quiet: bool = True,
) -> SessionResult
```

Create a virtual environment at *dest* and return a `SessionResult`.
Keyword arguments mirror the CLI options documented in {doc}`cli`;
`symlinks`/`copies` of `None` select the platform default (copies on
Windows, symlinks elsewhere). `quiet=False` streams progress to stdout at
default verbosity.

## `tn_venv.cli_run`

```python
def cli_run(args: list[str] | None = None, *, environ: dict[str, str] | None = None) -> int
```

Run the full CLI in-process and return its {doc}`exit code <exit-codes>`.
`args` excludes the program name. `environ` replaces `os.environ` for
configuration resolution (useful in tests).

## `tn_venv.SessionResult`

| Attribute | Type | Meaning |
|---|---|---|
| `env_dir` | `Path` | environment root directory |
| `exe` | `Path` | the environment's Python executable |
| `bin_path` | `Path` | `Scripts/` (Windows) or `bin/` (POSIX) |
| `site_packages` | `Path` | the environment's site-packages directory |
| `prompt` | `str` | prompt baked into the activation scripts |
| `python` | `PythonInfo` | probe of the base interpreter |
| `activation_scripts` | `list[Path]` | every activation script written |
| `seed` | `SeedResult \| None` | seeder outcome (`None` when seeding was off) |

## `tn_venv.seed.SeedResult`

| Attribute | Type | Meaning |
|---|---|---|
| `pip` | `str \| None` | installed pip version |
| `setuptools` | `str \| None` | `"installed"` when setuptools was installed |
| `wheel` | `str \| None` | `"installed"` when wheel was installed |
| `packages` | `list[str]` | `--with` specifiers that were installed |
| `requirements` | `list[str]` | requirement files that were installed |
| `skipped` | `bool` | `True` when the seeder ran as a no-op |

## `tn_venv.discovery.PythonInfo`

Immutable description of a probed interpreter.

| Attribute / property | Type | Meaning |
|---|---|---|
| `executable` | `str` | absolute path of the probed executable |
| `base_executable` | `str` | `sys._base_executable` — the real (non-venv) binary |
| `version_info` | `tuple[int, int, int]` | major, minor, micro |
| `version_str` | `str` | `"3.14.7"`-style rendering |
| `major_minor` | `str` | `"3.14"`-style rendering |
| `implementation` | `str` | `cpython`, `pypy`, … |
| `prefix` / `base_prefix` | `str` | installation prefixes |
| `bits` / `is_64` | `int` / `bool` | pointer width of the interpreter |
| `is_freethreaded` | `bool` | built with `Py_GIL_DISABLED` |
| `is_python_build` | `bool` | running from a build tree rather than an install |
| `base_dir` | `str` | directory of `base_executable` (the `pyvenv.cfg` `home`) |
| `scripts_nt` | `str \| None` | directory holding `venvlauncher.exe` (Windows only) |
| `matches(spec)` | `bool` | whether this interpreter satisfies an `InterpreterSpec` |

Construct with `PythonInfo.from_current()` (no subprocess) or
`PythonInfo.from_exe(path)` (probes by executing *path*; results are
cached per process).

## `tn_venv.discovery.discover`

```python
def discover(specs: str | list[str] | None = None, *, report: Reporter = SILENT) -> PythonInfo
```

Resolve the first satisfiable spec (see {doc}`../guide/interpreters`) and
return its probe. Raises `InterpreterNotFoundError` when nothing matches.
`discover_all()` returns `(PythonInfo, source)` pairs for every candidate
every provider can find.

## Exceptions

```text
TnVenvError                     # base class
├── ConfigError             # bad options, env vars, or config file
├── DiscoverError           # interpreter probing failed
│   └── InterpreterNotFoundError   # .spec, .tried
├── CreateError             # could not lay down the environment
├── ActivateError           # activation script generation failed
├── SeedError               # ensurepip / pip step failed
├── LockError               # destination lock timed out
└── SubprocessError         # .cmd, .returncode, .output
```

All are importable from the package root (`from tn_venv import TnVenvError, …`).
