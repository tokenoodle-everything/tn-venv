# Changelog

All notable changes to tn-venv are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] — 2026-09-13

### Added
- Full documentation site under `docs/` (Sphinx + MyST): user guide, CLI /
  env-var / config-file references, architecture and extension manuals.
- Expanded test suite: per-module coverage for discovery providers,
  creators, activators, seeder, config, and utilities.

## [0.1.0] — 2026-09-12

Initial public release.

### Added
- One-command creation: bare `tn-venv` builds `./.venv` with pip installed.
- Interpreter discovery from PATH, the Windows registry (PEP 514), the `py`
  launcher (PEP 397), uv-managed installs, and pyenv; `-p` accepts paths,
  versions (`3.12`), command names, and implementation specs (`pypy3.10`).
- Platform-native creators: Windows copies `venvlauncher` redirectors with
  a real-binary + DLL fallback; POSIX symlinks with copy fallback.
- Seeding via `ensurepip`, with pip pinning (`--pip 24.0`), index upgrades
  (`--upgrade-pip`), `setuptools`/`wheel`, `--with PKG` and `-r FILE`
  installation at creation time, `--extra-search-dir`, and `--offline`.
- Activation scripts for bash/zsh, cmd.exe, PowerShell, fish, csh/tcsh,
  Nushell, plus `activate_this.py`.
- Layered configuration: CLI flags > `TN_VENV_*` environment variables >
  config files (`pyproject.toml`, `tn-venv.ini`, `.tn-venv.toml`,
  `setup.cfg`) > defaults; `--dry-run` to inspect the result.
- `--clear` / `--upgrade` lifecycle management with an inter-process file
  lock (stale-lock reclamation included).
- Python API: `tn_venv.create_venv()` and `tn_venv.cli_run()`.
