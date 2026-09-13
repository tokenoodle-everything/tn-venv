# Security policy

The binding document is {download}`SECURITY.md <../../SECURITY.md>` in the
repository root. Summary:

## Reporting a vulnerability

Do not open a public issue. Email the maintainers listed in `SECURITY.md`
with a description, reproduction steps, and the affected versions. You will
receive an acknowledgement within 72 hours.

## Scope notes

`tn-venv` executes two kinds of external code, both by design and both
worth understanding before reporting:

1. **Candidate interpreters.** Discovery *executes* every Python it finds
   to probe it. An attacker who can place a fake `python.exe` on your
   `PATH` (or in a registry hive you control) can already execute code as
   you; this is not a tn-venv privilege escalation.
2. **pip inside the new environment.** Seeding runs pip with network access
   unless `--offline` is used. Package resolution attacks (typosquatting,
   dependency confusion) are pip-index concerns; use `--extra-search-dir`,
   `--offline`, or pinned requirement files to constrain them.

`tn-venv` itself never evaluates config files (TOML/INI are parsed, not
executed), never downloads interpreters, and never writes outside the
destination directory other than its transient lock file.
