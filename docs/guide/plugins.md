# Plugins

> **The full plugin reference lives in {doc}`../plugins/index`.**
>
> This page is a navigation pointer. The authoritative
> documentation for the plugin system — quickstart, discovery,
> hooks, authoring, CLI integration, and the API reference — is in
> `docs/plugins/`. The original tutorial content that used to live
> here has moved there; this guide now links to the relevant section
> of `docs/plugins/`.

## Quick links

| If you want to… | Go to |
|---|---|
| Write your first plugin | {doc}`../plugins/quickstart` |
| Understand how plugins are loaded | {doc}`../plugins/discovery` |
| See the full hook reference | {doc}`../plugins/hooks` |
| Use the Plugin / HookRegistry / HookContext API | {doc}`../plugins/authoring` |
| Add text to tn-venv --list-plugins, customise --help, or install a CLI subcommand | {doc}`../plugins/cli-integration` |
| Look up a specific symbol | {doc}`../plugins/reference` |

## Overview

`tn-venv` ships with a small plugin system that lets you tap into the
creation pipeline at six well-defined points. Plugins can read and
modify the `Options`, peek at the freshly built `CreatorContext`,
append activation scripts, stamp metadata into `pyvenv.cfg`,
install extra packages, log information, or short-circuit parts of
the process — all without forking `tn-venv`.

The default install includes one built-in plugin
(`VersionStampPlugin`) that writes
`tn-venv-version = <version>` into `pyvenv.cfg` after the activation
scripts are generated. For the full story, see
{doc}`../plugins/index`.

