# Contributing to tn-venv

Thank you for your interest in improving tn-venv. This is the project’s
contribution guide; a rendered copy also appears in the documentation under
Development → Contributing.

## Scope of contributions

Bug reports, documentation fixes, new tests, and well-scoped feature work are
all welcome. Features that add runtime dependencies are not: tn-venv must
remain importable using the Python standard library alone.

## Before you start

- Python 3.11 or newer is required.
- Use a dedicated branch off `master` for your work.
- Keep changes focused; avoid unrelated refactors.

## Development setup

```bash
git clone https://github.com/tokenoodle-everything/tn-venv.git
cd tn-venv
tn-venv .venv --with pytest
# Windows:  .venv\Scripts\activate.bat
# POSIX:    source .venv/bin/activate
python -m pytest
```

This creates the development environment with tn-venv itself installed and the
pytest dependency available.

## Rules for code changes

1. Declare options once. New CLI options belong in
   `tn_venv/config/spec.py`; the parser, environment-variable loader, and
   config-file loader all derive from that table. Do not add or edit CLI
   arguments by hand in `cli.py`.
2. Raise typed failures. Anticipated failures should raise a subclass of
   `tn_venv.errors.TnVenvError`; avoid bare `Exception` and avoid `sys.exit`
   outside `cli.py`.
3. Guard platform-specific code. Windows-only and POSIX-only paths must be
   protected by `os.name` / `sys.platform`, and each platform-specific path
   should have a skip-marked test.
4. Send subprocess work through `tn_venv.util.process.run_cmd`. This keeps
   `-vv` output and error wrapping consistent across the project.
5. Match the existing code style. Use `from __future__ import annotations`,
   dataclasses for structured data, and docstrings on public functions.

## Tests

Every behavior change should ship with tests:

- unit tests for pure logic (no network, no pip, no real environments);
- one integration test for anything that crosses a subprocess boundary;
- platform-specific tests behind a skip guard so the suite stays green on all
  supported platforms.

Run `python -m pytest` before opening a pull request. The full suite must pass;
skipped platform tests are expected and fine.

## Documentation

If your change is user-visible, update the relevant page under `docs/`.
A flag that is not in the CLI reference is effectively invisible to users.

The docs build with:

```bash
pip install -r docs/requirements.txt
sphinx-build -M html docs docs/_build
```

## Pull requests

- Branch from `master`.
- Keep the change focused.
- Describe the observable behavior change in the PR body so the changelog can
  be updated accurately.
- By contributing, you agree that your contribution is licensed under the
  project’s `License.txt`.

## Code of conduct

Participation is governed by `CODE_OF_CONDUCT.md`.
