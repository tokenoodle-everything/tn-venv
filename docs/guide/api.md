# Using tn-venv from Python

The CLI is a thin wrapper over a programmatic API, so build scripts,
test harnesses, and installer tools can create environments without
shelling out.

## The one-call API

```python
from tn_venv import create_venv

result = create_venv(
    ".venv",
    python="3.12",                  # str, list of specs, or None
    clear=False,
    upgrade=False,
    system_site_packages=False,
    copies=None,                    # None = platform default
    with_pip=True,
    pip="24.0",                     # None | "latest" | exact version
    setuptools=True,                # bool or pinned version string
    wheel=True,
    upgrade_pip=False,
    packages=["requests"],
    requirements=["dev-requirements.txt"],
    activators=["bash", "powershell"],
    prompt="my-project",
    offline=False,
    extra_search_dir=["/srv/wheels"],
    quiet=True,                     # False = stream progress to stdout
)
```

`create_venv()` returns a `SessionResult`:

```python
result.env_dir             # Path — the environment directory
result.exe                 # Path — the environment's python executable
result.bin_path            # Path — Scripts/ (Windows) or bin/ (POSIX)
result.site_packages       # Path — the environment's site-packages
result.prompt              # str — the prompt baked into activation scripts
result.python              # PythonInfo — the probed base interpreter
result.activation_scripts  # list[Path] — every script that was generated
result.seed                # SeedResult | None — what the seeder installed
```

`result.seed` is `None` when seeding was disabled (`with_pip=False`);
otherwise it records the installed `pip` version, whether `setuptools` and
`wheel` were installed, and which `packages` / `requirements` were applied.

`result.python` carries the full probe of the base interpreter —
`version_info`, `implementation`, `base_executable`, `bits`,
`is_freethreaded`, and more. See {doc}`../reference/python-api`.

## Errors

All deliberate failures raise from a single hierarchy:

```python
from tn_venv import TnVenvError, InterpreterNotFoundError, CreateError, SeedError

try:
    create_venv("/srv/app/.venv", python="3.99")
except InterpreterNotFoundError as exc:
    print(exc.spec, exc.tried)   # the spec and every candidate probed
except TnVenvError as exc:
    print("creation failed:", exc)
```

| Exception | Raised when |
|---|---|
| `ConfigError` | options are contradictory or malformed |
| `InterpreterNotFoundError` | no candidate satisfies any `--python` spec |
| `DiscoverError` | a candidate executable cannot be probed |
| `CreateError` | the destination cannot be created or binaries installed |
| `SeedError` | ensurepip/pip fails inside the new environment |
| `LockError` | the destination lock cannot be acquired in time |

## Running the CLI in-process

```python
from tn_venv import cli_run

exit_code = cli_run([".venv", "--clear", "-p", "3.12"])
```

`cli_run()` parses arguments, applies the full configuration stack
(env vars and config files included, unless `--no-config`), and returns the
process exit code — `0`, `1`, `2`, or `130` — as documented in
{doc}`../reference/exit-codes`. Pass `environ={...}` to run it against a
controlled environment.
