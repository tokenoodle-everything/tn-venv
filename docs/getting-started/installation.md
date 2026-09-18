# Installation

## Requirements

`tn-venv` runs on **Python 3.11 or newer** and has **no runtime
dependencies** — it is pure standard-library Python. The interpreter used to
*run* `tn-venv` and the interpreter used to *build* an environment may
differ: environments can be created for any CPython ≥ 3.8 or PyPy
interpreter that `tn-venv` can execute.

Supported host platforms:

- Windows 10/11 (x86-64), including environments without Developer Mode
- macOS (Intel and Apple silicon)
- Linux and other POSIX systems with a standards-compliant `symlink(2)`

## From PyPI

```console
$ pip install tn-venv
```

This registers two console scripts — `tn-venv` and its alias `tn_venv` —
and makes `python -m tn_venv` available.

## From source

```console
$ git clone https://github.com/tokenoodle-everything/tn-venv.git
$ cd tn-venv
$ pip install .
```

For development work, install in editable mode with the test suite:

```console
$ pip install -e .
$ python -m pytest
```

## Verifying the installation

```console
$ tn-venv --version
tn-venv your.release.version

$ tn-venv --list-pythons
==> discovering interpreters…
  3.14.7 (64-bit)  C:\Python314\python.exe  — current
```

## Running without installing

Because the package has no dependencies, it can be executed straight from a
source checkout:

```console
$ python path/to/tn-venv/tn_venv/__main__.py --help
```

or, with the repository root on `PYTHONPATH`:

```console
$ python -m tn_venv .venv
```
