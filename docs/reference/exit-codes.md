# Exit codes

`tn-venv` uses a small, stable set of process exit codes so automation can
react without parsing output.

| Code | Meaning | Typical causes |
|---|---|---|
| `0` | success | environment created; `--list-pythons`, `--dry-run`, `--help`, `--version` completed |
| `1` | execution failure (`TNError`) | destination already contains an environment; interpreter not found; ensurepip/pip failed; lock timed out; requirements file missing |
| `2` | usage / configuration error | unknown flag; invalid choice; `--symlinks` with `--copies`; malformed config file or env var; unknown activator |
| `130` | interrupted | Ctrl+C during creation |

Rules of thumb for scripts:

- `2` means *fix the invocation* — retrying unchanged will fail again.
- `1` means *fix the environment* — the lock, the network, or the
  destination state.
- The error class is always printed as part of the message, and `-vv`
  shows the failing subprocess command and its full output.

`cli_run()` (see {doc}`python-api`) returns exactly these codes, so
embedding code can rely on the same contract.
