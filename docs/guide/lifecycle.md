# Environment lifecycle

Creating, refreshing, and replacing environments — and what protects you
when two processes try to do it at once.

## Create

```console
$ tn-venv .venv
```

Creation refuses to overwrite an **existing environment** unless you say
otherwise: if `DEST/pyvenv.cfg` already exists and neither `--clear` nor
`--upgrade` was given, the command fails with exit code 1. A pre-existing
*non-environment* directory (no `pyvenv.cfg`) is reused in place, matching
the behaviour of `python -m venv`.

One hard rule: the destination path must not contain the platform's `PATH`
separator (`;` on Windows, `:` on POSIX). Such a path would corrupt every
activation script, so creation is refused up front with exit code 1.

## Upgrade in place

```console
$ tn-venv .venv --upgrade
```

`--upgrade` rewrites the interpreter binaries, `pyvenv.cfg`, and the
activation scripts, and re-runs the seeder (`ensurepip --upgrade`), **without
touching `site-packages`**. Use it after the base interpreter was updated
(e.g. 3.12.4 → 3.12.8) to re-point the environment at the new binaries.

Running `--upgrade` against a destination that does not exist simply
creates it — the flag is idempotent.

## Clear and recreate

```console
$ tn-venv .venv --clear
```

`--clear` deletes the entire destination directory — including
`site-packages` and anything else you left in it — before creating the
fresh environment. On Windows, read-only files are made writable during
deletion, so checked-out or locked-against-deletion artifacts do not block
recreation.

When `--clear` and `--upgrade` are combined, `--clear` wins: the directory
is removed first and `--upgrade` becomes a no-op.

(concurrency-locking)=
## Concurrency and locking

Every creation runs under an inter-process file lock named
`DEST.tn-venv.lock`, created next to the destination with
`O_CREAT | O_EXCL`:

- A second `tn-venv` process targeting the same directory waits, polling
  every 50 ms, for up to **120 seconds**.
- The lock file records the holder's pid, host, and timestamp. If the
  holder's pid is dead and the lock is older than 600 seconds, the lock is
  considered **stale** and is reclaimed automatically — a crashed process
  can never wedge a directory forever.
- When the timeout expires, creation fails with a `LockError`
  (exit code 1) that names the lock file.

The lock is released whether creation succeeds, fails, or is interrupted.

## What lands on disk

The exact per-platform file layout is documented in
{doc}`../reference/environment-layout`; `pyvenv.cfg` keys are enumerated in
{doc}`../reference/pyvenv-cfg`.
