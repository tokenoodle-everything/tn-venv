# Architecture

`tn-venv` is a four-stage pipeline wrapped in a configuration system. Each
stage is a package with a narrow contract, and the stages never see each
other's internals — they exchange two data structures: `PythonInfo` (the
probe of the base interpreter) and `CreatorContext` (the paths of the
environment being built).

```text
                 ┌────────────────────────── tn_venv.cli ──────────────────────────┐
                 │  argparse (driven by config/spec.py) → exit codes               │
                 └──────────────────────────────┬──────────────────────────────────┘
                                                 │
                    tn_venv.config: CLI ◄ env vars ◄ config file ◄ defaults
                                                 │
                                        tn_venv.session
                                    (Options → run_session)
                                                 │
        ┌──────────────┬────────────────────────┼───────────────────────┬──────────────┐
        ▼              ▼                        ▼                       ▼              ▼
  tn_venv.       tn_venv.create          tn_venv.create.        tn_venv.seed    tn_venv.report
  discovery      (Creator per platform)  activators             (Seeder)        (leveled output)
        │              │                        │                       │
   PythonInfo ──▶ CreatorContext ──▶ activation scripts ──▶ pip/setuptools/…
```

## Package map

| Module | Responsibility |
|---|---|
| `tn_venv.cli` | argument parsing, config layering, exit codes, `--list-pythons`, `--dry-run` |
| `tn_venv.config.spec` | the single source of truth for every option (`OPTION_SPECS`) |
| `tn_venv.config.loader` | TOML/INI/env-var loading and coercion |
| `tn_venv.session` | `Options`, the pipeline, `SessionResult`, the public `create_venv()` |
| `tn_venv.discovery` | spec parsing, providers, probing, matching |
| `tn_venv.create.creator` | `Creator` base, `WindowsCreator`, `PosixCreator` |
| `tn_venv.create.context` | `CreatorContext` — the stage contract |
| `tn_venv.create.activators` | one module per shell, template-based |
| `tn_venv.seed.seeder` | `PipSeeder` (ensurepip → pin/upgrade → extras) |
| `tn_venv.util.lock` | inter-process file lock with stale detection |
| `tn_venv.util.process` | subprocess wrapper with captured output |
| `tn_venv.report` | leveled, colored console output |
| `tn_venv.errors` | the exception hierarchy |

## Design rules

1. **No runtime dependencies.** Everything is stdlib. Optional behavior
   degrades instead of failing (e.g. a missing `py` launcher is a skipped
   provider, not an error).
2. **One source of truth per concern.** Options exist once, in
   `OPTION_SPECS`; platform branching exists once, in the creator factory;
   quoting rules exist once, in the activator base class.
3. **Probe, don't guess.** Interpreter facts (version, bitness, free-threading,
   launcher locations) come from executing the interpreter itself, never
   from parsing paths or filenames.
4. **Mirror `venv` semantics.** Where stdlib `venv` has an opinion —
   directory layout, `pyvenv.cfg` keys, Windows launcher binaries, `lib64`
   symlinks — tn-venv adopts it, so environments stay interchangeable.
5. **Failures are typed.** Every anticipated failure raises a subclass of
   `TnVenvError`; the CLI maps them to documented exit codes and the API
   re-raises them unmodified.

## Data flow in detail

1. **CLI** parses flags with `default=None` everywhere, so "not supplied"
   is distinguishable from "supplied as false".
2. **Config** merges layers into a plain dict: defaults ← file ← env ← CLI.
3. **Session** turns the dict into a validated `Options` dataclass and
   acquires the destination lock.
4. **Discovery** resolves `--python` specs to a probed `PythonInfo`
   (subprocess JSON probe, cached).
5. **Creator** builds the skeleton (`ensure_directories`), installs the
   interpreter binaries (`setup_python`), writes `pyvenv.cfg`
   (`create_configuration`) and the SCM ignore file.
6. **Activators** render their templates against `CreatorContext` with
   shell-appropriate quoting.
7. **Seeder** invokes the *new* interpreter with a scrubbed environment
   (`PYTHONHOME`/`PYTHONPATH` removed, `VIRTUAL_ENV` set) for ensurepip and
   all pip steps.
8. The lock is released and a `SessionResult` is returned; the CLI prints
   the activation hint.

## Concurrency model

Creation is serialised per destination directory by
{ref}`the file lock <concurrency-locking>`. Parallel
creations of *different* destinations are fully independent — `tn-venv`
holds no global mutable state beyond the per-process probe cache.
