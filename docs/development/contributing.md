# Contributing

Contributions are welcome. This page is the short version; the binding
document is {download}`CONTRIBUTING.md <../../CONTRIBUTING.md>` in the
repository root, and participation is governed by the
{download}`Code of Conduct <../../CODE_OF_CONDUCT.md>`.

## Ground rules

1. **No new runtime dependencies.** The tool must stay importable with the
   standard library alone. Dev-time tools (pytest, Sphinx) are fine.
2. **Options are declared once.** Add flags through
   `tn_venv/config/spec.py`, never by hand-editing the parser.
3. **Behavior changes need tests.** Unit tests for logic; one integration
   test when a subprocess boundary is crossed. See {doc}`testing`.
4. **Docs are part of the feature.** A flag that is not in
   {doc}`../reference/cli` does not exist as far as users are concerned.

## Workflow

```console
$ git clone https://github.com/tokenoodle-everything/tn-venv.git
$ cd tn-venv
$ tn-venv .venv --with pytest          # dogfood: create the dev env with tn-venv itself
$ .venv\Scripts\activate.bat           # or: source .venv/bin/activate
$ python -m pytest
```

Branch from `master`, keep commits focused, and end the PR description with
a summary of behavioral changes so the changelog can be updated.

## Reporting bugs

Open an issue with:

- the exact command line (or `create_venv()` call);
- `tn-venv --version` and the host platform;
- the failing output, re-run with `-vv` so the failing subprocess and its
  output are visible.

For security issues, do **not** open a public issue — see
{doc}`security`.
