# Hooks

The pipeline emits **six** events at well-defined points. Five are
*lifecycle* hooks (they fire during `tn_venv.session.run_session`).
The sixth, `HELP_EPILOG`, is special: it fires only when the user
asks for `tn-venv --help`, and its listener returns a string
instead of mutating a `HookContext`.

This page is the canonical reference for every hook's timing,
payload, and fault-isolation contract.

## The six hooks at a glance

| Hook | When | Listener payload | `ctx.data` keys populated by the pipeline |
|---|---|---|---|
| `SESSION_START` | after option resolution and interpreter discovery, before the destination lock | `HookContext(options, reporter, data={})` | `{}` |
| `PRE_CREATE` | immediately before `Creator.create()` | `HookContext(options, reporter, data={})` | `{}` |
| `POST_ACTIVATORS` | after every activation script has been written, before seeding | `HookContext(options, reporter, data={cfg_path, env_dir, scripts})` | `cfg_path`, `env_dir`, `scripts` |
| `POST_SEED` | after the seeder finishes (or skips) | `HookContext(options, reporter, data={cfg_path, env_dir, scripts, seed_result})` | `cfg_path`, `env_dir`, `scripts`, `seed_result` |
| `SESSION_END` | last, just before `run_session` returns | `HookContext(options, reporter, result=…, data={cfg_path, env_dir, scripts, seed_result})` | all of the above plus `result` (a `SessionResult`) |
| `HELP_EPILOG` | when `tn-venv --help` is rendered (CLI only) | n/a — listener returns `str \| None` instead of taking `ctx` | n/a |

The lifecycle hooks fire **in this order** during a normal run, but
the CLI is allowed to short-circuit (`--help`, `--version`,
`--list-plugins`, `--list-pythons`, `--dry-run`) before any of them.
A plugin that depends on `SESSION_END` running should not assume
`--help` will ever fire it.

## `HookContext`

Every lifecycle hook receives a single argument — a `HookContext`:

```python
@dataclass
class HookContext:
    options: Options | None          # the resolved Options
    reporter: Reporter | None        # for warn / info / debug / ok
    result: SessionResult | None     # populated for SESSION_END only
    data: dict[str, Any]             # per-run scratch space
```

`data` is **shared** across every hook of the same run. The pipeline
populates it incrementally:

| After hook | `ctx.data` contains |
|---|---|
| `SESSION_START` | `{}` |
| `PRE_CREATE` | `{}` |
| `POST_ACTIVATORS` | `cfg_path` (Path), `env_dir` (Path), `scripts` (list[Path]) |
| `POST_SEED` | `cfg_path`, `env_dir`, `scripts`, `seed_result` (SeedResult or None) |
| `SESSION_END` | same, plus `result` is populated on the context itself |

Plugins may add their own keys (e.g. `data["my_plugin_started_at"] =
time.time()`). Two plugins that write to the same key collide — last
writer wins. The pipeline's own keys are reserved (`cfg_path`,
`env_dir`, `scripts`, `seed_result`, `result`).

`ctx.options` may be `None` for hooks fired outside a real session
(test paths, programmatic invocations). Always guard with
`if ctx.options is not None:` or use `getattr(ctx, "options", None)`.

`ctx.result` is only populated for `SESSION_END`. Other lifecycle hooks
see `None`. Plugins can read `ctx.result.env_dir` etc. during
`SESSION_END` to build side-effects that need the final path.

## Listener signature

Lifecycle hooks: a single positional `HookContext` argument. Must
return `None`. Returning anything else is silently ignored today
and will become a `TypeError` in a future release.

```python
def my_listener(ctx: HookContext) -> None:
    if ctx.options and ctx.options.python:
        ctx.reporter.info(
            f"asked for Python {ctx.options.python[0]}"
        )
```

`HELP_EPILOG` hooks: **no arguments**, return `str | None`. The
loader concatenates non-`None` returns with a blank-line separator.
Returning `None` (or an empty string) opts the plugin out for that
invocation.

```python
def my_help_text() -> str | None:
    return "extras from my_plugin:\n  thing one\n  thing two"
```

## Priority

`hooks.add(hook, fn, priority=N)` controls dispatch order. **Higher
priorities run first**. Ties keep insertion order. `DEFAULT_PRIORITY`
is `100`. Built-ins typically use lower numbers so user plugins run
before them.

```python
hooks.add(
    HookName.POST_ACTIVATORS,
    my_func,
    priority=200,        # runs before priority=100, which runs before 0
    plugin_name=self.name,
)
```

Priority is per-hook: a `priority=200` listener on `SESSION_START`
has no effect on `POST_ACTIVATORS` ordering.

## Multiple registrations

A plugin can register the same listener under multiple hooks, or
multiple listeners under the same hook:

```python
class Multi(Plugin):
    def register(self, hooks):
        # Same function on three hooks — fine:
        hooks.add(HookName.SESSION_START, self._log_start, plugin_name=self.name)
        hooks.add(HookName.POST_ACTIVATORS, self._log_start, plugin_name=self.name)
        hooks.add(HookName.SESSION_END, self._log_end, plugin_name=self.name)
```

Listeners run in priority order; ties keep insertion order.

## Fault isolation

A listener that raises an exception is **logged and ignored**. The
pipeline keeps running. Other listeners on the same hook still fire;
later hooks still fire; the `SessionResult` is still returned
normally.

The warning goes through the `Reporter` passed in the context, or
the registry's reporter if the context's is `None`. Programmatic
callers who don't want warnings should pass
`reporter=tn_venv.report.SILENT` to `load_plugins`.

## Subclassing `Plugin` to override the default

The default `Plugin.register()` is a no-op. Subclasses override it:

```python
class MyPlugin(Plugin):
    name = "my_plugin"

    def register(self, hooks) -> None:
        hooks.add(
            HookName.SESSION_END,
            self._on_end,
            priority=50,            # run after built-ins
            plugin_name=self.name,
        )

    def _on_end(self, ctx: HookContext) -> None:
        env_dir = ctx.result.env_dir
        # ...
```

`Plugin.__init_subclass__` auto-fills `cls.name` from the class name
if you don't set it. **Always set `name` explicitly** so a later
rename doesn't change the plugin's identifier.

## The `Plugin` API at a glance

```python
class Plugin:
    name: str = ""             # identifier (stable identifier)

    def __init_subclass__(cls, **kwargs): ...     # auto-fills name

    def register(self, hooks: HookRegistry) -> None:
        """Install hook callbacks on *hooks*.

        Subclasses override this to participate in the session
        lifecycle. The default implementation registers nothing, so
        a plugin with no override is effectively a no-op.
        """
```

The full reference for `HookRegistry` (which the `register()` hook
gets passed) is in {doc}`authoring`.

## Recipes

### Stamping a build tag into `pyvenv.cfg`

```python
class BuildStamp(Plugin):
    name = "build_stamp"

    def register(self, hooks):
        def _stamp(ctx):
            cfg = ctx.data.get("cfg_path")
            if cfg is None or not cfg.exists():
                return
            with cfg.open("a", encoding="utf-8") as fh:
                fh.write(f"\n# build-stamp: {time.time()}\n")
        hooks.add(HookName.POST_ACTIVATORS, _stamp, plugin_name=self.name)
```

### Reporting the install side-effect to a log file

```python
class InstallLog(Plugin):
    name = "install_log"
    LOG = Path("/var/log/tn-venv.jsonl")

    def register(self, hooks):
        hooks.add(HookName.SESSION_END, self._on_end, plugin_name=self.name)

    def _on_end(self, ctx):
        with self.LOG.open("a") as fh:
            fh.write(json.dumps({
                "env_dir": str(ctx.result.env_dir),
                "seed": getattr(ctx.result.seed, "pip", None),
            }) + "\n")
```

### Logging the user's effective options

```python
class OptionLogger(Plugin):
    name = "option_logger"

    def register(self, hooks):
        @hooks.add(HookName.SESSION_START, plugin_name=self.name)
        def _log(ctx):
            ctx.reporter.info(f"effective options: {ctx.options!r}")
```

### Failing loudly on a bad configuration

```python
class RequiredPython(Plugin):
    name = "required_python"
    MIN = (3, 11)

    def register(self, hooks):
        hooks.add(HookName.PRE_CREATE, self._check, plugin_name=self.name)

    def _check(self, ctx):
        if not ctx.options:
            return
        spec = ctx.options.python[0] if ctx.options.python else None
        if spec is None:
            raise ConfigError("--python is required when this plugin is loaded")
        # ... parse `spec` and compare ...
```

Note the deliberate `raise`. The loader catches it, logs a warning,
and skips the plugin. The pipeline continues without this plugin's
hooks. Use this pattern sparingly — failing loud on bad data is good
when done in a `ConfigError`, but the fault-isolation layer means
**the pipeline never aborts because of a plugin error**.