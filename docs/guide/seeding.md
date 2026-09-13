# Seeding: pip, setuptools, wheel, and beyond

"Seeding" is the step that installs a package installer into the fresh
environment. `tn-venv`'s seeder is built on the standard library's
`ensurepip` and then goes well beyond it.

## The default: bundled pip

```console
$ tn-venv .venv
```

runs, inside the new environment:

```text
python -Im ensurepip --upgrade --default-pip
```

`ensurepip` installs the pip wheel **bundled with the interpreter**, so the
default path never touches the network and works on air-gapped machines.
On completion, the seeder reports the installed pip version.

```{note}
Since Python 3.12, `ensurepip` no longer bundles `setuptools`. Recreate the
classic trio explicitly with `--setuptools --wheel` if your workflow needs
them.
```

## Choosing the pip version

| Invocation | Effect |
|---|---|
| *(default)* | install the pip bundled with the interpreter |
| `--pip 24.0` | install exactly `pip==24.0` from the index |
| `--pip` / `--pip latest` | install/upgrade to the latest released pip |
| `--pip bundled` | explicit no-op form of the default |
| `--upgrade-pip` | shorthand for `--pip latest` |

`--upgrade-pip` takes precedence over `--pip VERSION` when both are given.

## setuptools and wheel

Both options accept an optional version in exactly the same way:

```console
$ tn-venv .venv --setuptools --wheel
$ tn-venv .venv --setuptools 69.0.3 --wheel 0.43.0
```

## Installing packages straight into the new environment

```console
$ tn-venv .venv --with requests --with "click>=8,<9"
$ tn-venv .venv -r requirements.txt -r dev-requirements.txt
```

- `--with` (alias `--seed-package`) accepts any pip requirement specifier
  and is repeatable.
- `-r` / `--requirements` accepts a pip requirements file and is
  repeatable; a missing file fails with a `SeedError` naming the path.

Install order is fixed and deterministic: bundled pip → pip pin/upgrade →
`setuptools`/`wheel` → `--with` packages → each `-r` file in order. Every
step runs with `--quiet`; add `-v`/`-vv` to the `tn-venv` invocation to see
the underlying commands and their full output.

## Offline and proxied environments

```console
$ tn-venv .venv --offline --extra-search-dir /srv/wheels
```

- `--extra-search-dir DIR` (repeatable) exports
  `PIP_FIND_LINKS=DIR1:DIR2:…` for every pip invocation, so local wheels
  and sdists are preferred.
- `--offline` exports `PIP_NO_INDEX=1`: pip never contacts an index.
  Bundled `ensurepip` still works (it is local by definition), but
  `--pip latest`, `--setuptools`, `--wheel`, `--with`, and `-r` will fail
  unless their artifacts are reachable through `--extra-search-dir`.

## Reproducibility hygiene

Every pip invocation the seeder makes runs with:

| Setting | Why |
|---|---|
| `PIP_DISABLE_PIP_VERSION_CHECK=1` | no version-check phone-home, faster installs |
| `PIP_NO_INPUT=1` | never block on a prompt inside automation |
| `PYTHONHOME` / `PYTHONPATH` scrubbed | user-level settings cannot leak into the new environment |
| `VIRTUAL_ENV` set, `cwd` = the env dir | the new interpreter always sees itself as activated |
| `-I` (isolated) | user site-packages and `sitecustomize` are bypassed |

## Skipping seeding entirely

```console
$ tn-venv .venv --no-pip          # or: --seeder none
```

Both forms produce an environment with no installer at all — useful for
build images that mount dependencies read-only. `--no-pip` wins over
`--seeder pip` when both are present.
