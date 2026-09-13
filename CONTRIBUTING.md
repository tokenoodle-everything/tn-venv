# Contributing to tn-venv

Thank you for your interest in improving tn-venv. This document is the
binding contribution guide; a rendered copy lives in the documentation
under **Development → Contributing**.

## Scope of contributions

Bug reports, documentation fixes, new tests, and well-scoped features are
all welcome. Features that add runtime dependencies are not — tn-venv must
remain importable with the standard library alone.

## Development setup

```bash
git clone https://github.com/tokenoodle-everything/tn-venv.git
cd tn-venv
tn-venv .venv --with pytest        # create the dev environment with tn-venv itself
# Windows:  .venv\Scripts\activate.bat
# POSIX:    source .venv/bin/activate
python -m pytest
```

Requires Python 3.11 or newer.

## Rules for code changes

1. **Declare options once.** New CLI options go in
   `tn_venv/config/spec.py`; the parser, env-var loader, and config-file
   loader all derive from that table. Do not hand-edit `cli.py` for new
   options.
2. **Typed failures.** Raise a subclass of `tn_venv.errors.TNError` for any
   anticipated failure; never bare `Exception` or `sys.exit` outside
   `cli.py`.
3. **No unguarded platform code.** Windows-only and POSIX-only paths are
   guarded by `os.name` / `sys.platform`, with a skip-marked test for each
   side.
4. **Subprocesses go through `tn_venv.util.process.run_cmd`** so `-vv`
   output and error wrapping stay uniform.
5. **Match the existing style**: `from __future__ import annotations`,
   dataclasses for structured data, docstrings on public functions.

## Tests

Every behavior change ships with tests:

- unit tests for pure logic (no network, no pip, no real environments);
- one integration test for anything that crosses a subprocess boundary;
- platform-specific behavior is tested behind a skip guard so the suite is
  green everywhere.

Run `python -m pytest` before opening a pull request. The full suite must
pass; skipped platform tests are expected and fine.

## Documentation

If your change is user-visible, update the relevant page under `docs/` —
a flag that is not in the CLI reference does not exist for users. The docs
build with `sphinx-build -M html docs docs/_build` after
`pip install -r docs/requirements.txt`.

## Pull requests

Branch from `master`. Keep the change focused; describe observable behavior
changes in the PR body so the changelog can be updated. By contributing you
agree that your contribution is licensed under the project's
`License.txt`.

## Code of conduct

Participation is governed by `CODE_OF_CONDUCT.md`.
