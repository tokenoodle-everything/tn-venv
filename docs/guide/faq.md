# Frequently asked questions

## Is a tn-venv environment a "real" virtual environment?

Yes. The output is a [PEP 405](https://peps.python.org/pep-0405/)
environment with the same structure `python -m venv` produces:
`pyvenv.cfg`, platform binary layout, `site-packages`. `pip`, IDEs, `tox`,
and every other tool in the ecosystem consume it without knowing the
difference.

## Why does `--with requests` need the network but creation doesn't?

Creation itself — directories, binaries, `pyvenv.cfg`, activation scripts,
bundled pip — is fully local. Only *index-dependent* steps need the
network: `--pip latest`, `--upgrade-pip`, `--setuptools`, `--wheel`,
`--with`, and `-r`. Combine `--offline` with `--extra-search-dir` pointing
at a wheelhouse to run those steps without an index; see
{doc}`seeding`.

## How do I put a tn-venv environment under version control?

You don't — that is the point of the tool. `tn-venv` writes a `.gitignore`
containing `*` into the environment directory (disable with
`--scm-ignore none`), so even `git add -f` accidents are unlikely.
Recreate environments from a requirements file instead:
`tn-venv .venv --clear -r requirements.txt`.

## What does `--upgrade` actually change?

The interpreter binaries (`python.exe`/`pythonw.exe` or the `bin/python*`
links), `pyvenv.cfg`, the activation scripts, and pip (via
`ensurepip --upgrade`). Everything in `site-packages` is left alone. It is
the correct response to "the base Python got a patch update".

## Can tn-venv create an environment for a different Python than itself?

Yes — that is what {doc}`interpreters` is about. `tn-venv` running under
3.14 can create a 3.11 environment as long as it can *execute* the 3.11
interpreter for probing and seeding.

## Does it work in CI?

It is designed for it: non-interactive by construction
(`PIP_NO_INPUT=1`, pip's version check disabled), deterministic exit codes
({doc}`../reference/exit-codes`), `-q` for quiet logs, `--dry-run` for
config debugging, and a lock that makes parallel matrix jobs against a
shared workspace safe.

## How is this different from just running `python -m venv .venv`?

Feature for feature, see {doc}`comparison`. The one-line answer:
`tn-venv` is what `venv` would be with a decade of `virtualenv`'s lessons
applied — discovery, every shell, config files, seeding control — while
still producing byte-comparable output.

## Something failed. How do I see what actually happened?

Re-run with `-v` (progress detail) or `-vv` (full subprocess output):

```console
$ tn-venv .venv -vv
debug: $ C:\...\python.exe -Im ensurepip --upgrade --default-pip
  | ...
```

Every helper process `tn-venv` spawns is echoed at `-vv`, with its output
indented beneath it.
