# tn-venv vs venv, virtualenv, and uv

An honest feature comparison. Where another tool is better, this page says
so.

| | **tn-venv** | stdlib `venv` | `virtualenv` | `uv venv` |
|---|---|---|---|---|
| Zero runtime dependencies | ✅ | ✅ | ❌ (distlib, filelock, platformdirs) | ✅ (static binary) |
| Written in | Python | Python | Python | Rust |
| `pip` installed by default | ✅ | ✅ | ✅ | ❌ |
| `setuptools`/`wheel` seeding | ✅ optional | ❌ (3.12+) | ✅ | ❌ |
| Pin pip at creation (`--pip X.Y`) | ✅ | ❌ | ✅ (bundled wheel version) | ❌ |
| Offline seeding | ✅ bundled + `--extra-search-dir` | bundled only | ✅ app-data wheels | ✅ |
| `--with PKG` / `-r reqs.txt` at creation | ✅ | ❌ | ❌ | ❌ |
| Shells with activation scripts | 7 (bash, batch, ps1, fish, csh, nu, activate_this) | 3–4 | 5+ | 4 |
| `activate_this.py` | ✅ | ❌ | ✅ | ❌ |
| Interpreter discovery | PATH, PEP 514, `py`, uv, pyenv | current interpreter only | PATH, registry | PATH, managed downloads |
| Can *download* missing Pythons | ❌ | ❌ | ❌ | ✅ |
| Config files + env vars | ✅ `pyproject.toml`, ini, `TN_VENV_*` | ❌ | ✅ ini + env | ✅ env + config |
| `--dry-run` | ✅ | ❌ | ❌ | ❌ |
| Inter-process creation lock | ✅ | ❌ | ✅ (app-data) | ❌ |
| Speed (cold create, Windows) | ~2–4 s | ~2–5 s | ~0.5–1 s | ~0.05 s |
| Guarantees identical output to `python -m venv` | near-identical by design | ✅ by definition | ❌ | ❌ |

## When to choose what

- **`python -m venv`** — you are on a machine where installing anything is
  impossible, and you do not need `setuptools`, extra shells, or discovery.
  `venv` is always there.
- **`virtualenv`** — you need its app-data seed caching (faster repeated
  creation), its plugin ecosystem, or support for Python < 3.11 hosts.
- **`uv venv`** — raw creation speed is the bottleneck (CI creating
  thousands of environments), or you want `uv` to *download* the
  interpreter too.
- **`tn-venv`** — you want one memorable command with rigorous defaults,
  every shell's activation script, per-project config in
  `pyproject.toml`, package installation at creation time, and a tool you
  can read end-to-end because it is pure, dependency-free Python.

## Compatibility notes

Environments produced by `tn-venv` follow [PEP 405](https://peps.python.org/pep-0405/)
and are byte-comparable in structure to `python -m venv` output: same
directory layout, same `pyvenv.cfg` keys (plus a few documented extras,
see {doc}`../reference/pyvenv-cfg`), same binary placement on Windows
(`venvlauncher.exe` redirectors on Python ≥ 3.11). Anything that consumes a
standard virtual environment — IDEs, `pip`, `tox`, build frontends — treats
a `tn-venv` environment exactly like a `venv` one.
