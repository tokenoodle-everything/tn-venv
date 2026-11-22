# Security Policy


## Reporting a vulnerability

**Please do not open a public GitHub issue for security reports.**

Instead, report it privately through
[GitHub Security Advisories](https://github.com/tokenoodle-everything/tn-venv/security/advisories/new)
(Security → Advisories → "Report a vulnerability"), or email the
maintainers at **security@tokenoodle.com** — whichever you prefer.

Either way, please include:

- a description of the vulnerability and its impact;
- minimal reproduction steps;
- affected versions and platforms.

You will receive an acknowledgement within **72 hours** and a resolution
timeline within **14 days**. Once a fix is released, the advisory is
published publicly, and credit is given in the release notes unless you
prefer otherwise.

## Threat model notes

tn-venv executes external code in two places, both intentional:

1. **Interpreter discovery executes every candidate Python** to probe it.
   An attacker who can plant a fake `python.exe` on your `PATH` or in your
   registry hives can already run code as you; discovery does not widen
   that privilege boundary.
2. **Seeding runs pip**, which contacts a package index unless `--offline`
   is used. Supply-chain risks (typosquatting, dependency confusion) are
   inherent to pip; constrain them with pinned requirements,
   `--extra-search-dir`, and `--offline`.

tn-venv itself parses — never executes — configuration files, never
downloads interpreters, and writes only inside the destination directory
(plus its transient `*.tn-venv.lock` file).
