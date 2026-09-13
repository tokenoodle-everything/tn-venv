# Testing

## Running the suite

```console
$ python -m pytest
```

The suite lives in `tests/`, one module per source module:

| Test module | Covers |
|---|---|
| `test_cli.py` | parsing, `--dry-run`, `--list-pythons`, exit codes |
| `test_config_spec.py` | option specs and value coercion |
| `test_config_loader.py` | TOML/INI/env loading, discovery order, precedence |
| `test_discovery.py` | spec grammar, `discover()` paths |
| `test_discovery_providers.py` | PATH/registry/launcher/uv/pyenv providers |
| `test_discovery_python_info.py` | probing, caching, spec matching |
| `test_create_context.py` | the `CreatorContext` contract |
| `test_create_creator.py` | Windows/POSIX creators, pyvenv.cfg, clear/upgrade |
| `test_create_activators.py` | every template, quoting, placeholder leaks |
| `test_seed.py` | seeder command construction (subprocesses mocked) |
| `test_session_options.py` | `Options` validation and derived properties |
| `test_create_venv.py` | end-to-end creation, isolation checks |
| `test_errors.py`, `test_report.py` | exception text, leveled output |
| `test_util_lock.py`, `test_util_path.py`, `test_util_process.py` | utilities |
| `test_package.py` | packaging metadata and imports |

## Properties the suite guarantees

- **Unit tests never touch the network and never spawn pip.** Seeder tests
  intercept `run_cmd`; discovery tests use the running interpreter or fakes.
- **Integration tests create real environments** under `tmp_path` and then
  *execute the new interpreter* to verify `sys.prefix` isolation and pip
  presence. These are the slow tests; everything else is milliseconds.
- **Platform-specific tests skip cleanly.** POSIX symlink behavior is
  skipped on Windows and vice versa (`pytest.mark` / explicit guards), so
  the suite is green on every supported host.
- **No test depends on machine state.** An autouse fixture points
  `TN_VENV_CONFIG_FILE` at an empty file and strips ambient `TN_VENV_*`
  variables, so a developer's personal configuration can never leak into a
  test run.

## Building this documentation

```console
$ pip install -r docs/requirements.txt
$ sphinx-build -M html docs docs/_build          # POSIX
$ docs\make.bat html                              # Windows
```

The build uses Sphinx with MyST (Markdown), sphinx-design, the Read the
Docs theme, and sphinx-copybutton. `docs/conf.py` reads the release from
installed package metadata and falls back to `tn_venv/version.py` when the
package is not installed, so the docs build from a bare checkout.

## Coverage and hygiene

The suite passes with **315 tests** on CPython 3.14/Windows at the time of
writing. New features are expected to arrive with unit tests for logic and,
where the feature crosses a process boundary, one integration test that
runs the real thing.
