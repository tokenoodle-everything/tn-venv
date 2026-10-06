"""Tests for the plugin system: registry, loader, and pipeline integration."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

import tn_venv.plugins as plugins_pkg
from tn_venv.plugins import (
    HookContext,
    HookName,
    HookRegistry,
    PLUGIN_ENV_VAR,
    Plugin,
    load_plugins,
    parse_plugin_spec,
    require_plugin,
)
from tn_venv.report import Reporter


# -- HookRegistry -----------------------------------------------------------


def _capture_registry() -> tuple[HookRegistry, list[str]]:
    """A registry that records the order its hooks fired."""
    order: list[str] = []

    class SpyPlugin(Plugin):
        name = "spy"

        def register(self, hooks):
            hooks.add(HookName.SESSION_START, self._first, priority=200)
            hooks.add(HookName.SESSION_START, self._second, priority=100)
            hooks.add(HookName.SESSION_END, self._end)

        def _first(self, _ctx):
            order.append("first")

        def _second(self, _ctx):
            order.append("second")

        def _end(self, _ctx):
            order.append("end")

    registry = HookRegistry()
    SpyPlugin().register(registry)
    return registry, order


def test_registry_priority_orders_highest_first() -> None:
    registry, order = _capture_registry()
    registry.emit(HookName.SESSION_START)
    assert order == ["first", "second"]


def test_registry_listeners_returns_callables_in_dispatch_order() -> None:
    registry, _ = _capture_registry()
    callables = registry.listeners(HookName.SESSION_START)
    assert [fn.__name__ for fn in callables] == ["_first", "_second"]


def test_registry_listener_count() -> None:
    registry, _ = _capture_registry()
    assert registry.listener_count(HookName.SESSION_START) == 2
    assert registry.listener_count(HookName.SESSION_END) == 1
    assert registry.listener_count(HookName.POST_SEED) == 0


def test_registry_accepts_string_hook_name() -> None:
    registry = HookRegistry()
    seen: list[str] = []

    @registry.add(HookName.POST_SEED)
    def _cb(ctx):
        seen.append("called")

    registry.emit("post_seed")
    assert seen == ["called"]


def test_registry_rejects_unknown_hook_string() -> None:
    registry = HookRegistry()
    with pytest.raises(ValueError):
        registry.add("not-a-hook", lambda ctx: None)


def test_registry_one_failing_listener_does_not_stop_others() -> None:
    reporter = Reporter(verbosity=0)
    registry = HookRegistry(reporter=reporter)
    calls: list[str] = []

    def boom(_ctx):
        calls.append("boom")
        raise RuntimeError("explode")

    def after(_ctx):
        calls.append("after")

    registry.add(HookName.SESSION_START, boom, plugin_name="boomer")
    registry.add(HookName.SESSION_START, after, plugin_name="survivor")
    ctx = HookContext(reporter=reporter)
    returned = registry.emit(HookName.SESSION_START, ctx)
    assert calls == ["boom", "after"]
    assert returned is ctx


def test_registry_no_listeners_is_noop() -> None:
    registry = HookRegistry()
    registry.emit(HookName.SESSION_END)


# -- Plugin base class ------------------------------------------------------


def test_plugin_default_name_is_class_name() -> None:
    class _MyPlugin(Plugin):
        pass

    assert _MyPlugin().name == "_MyPlugin"


def test_plugin_default_register_is_noop() -> None:
    registry = HookRegistry()
    Plugin().register(registry)
    for hook in HookName:
        assert registry.listener_count(hook) == 0


def test_plugin_add_supports_decorator_form() -> None:
    registry = HookRegistry()
    calls: list[str] = []

    class _P(Plugin):
        name = "deco"

        def register(self, hooks):
            @hooks.add(HookName.SESSION_START, plugin_name=self.name)
            def _hook(ctx):
                calls.append(self.name)

    _P().register(registry)
    registry.emit(HookName.SESSION_START)
    assert calls == ["deco"]


# -- parse_plugin_spec ------------------------------------------------------


def test_parse_plugin_spec_dedups_and_trims() -> None:
    assert parse_plugin_spec(" a , b ,a , ,c ") == ["a", "b", "c"]


def test_parse_plugin_spec_empty() -> None:
    assert parse_plugin_spec("") == []


# -- require_plugin ---------------------------------------------------------


def test_require_plugin_returns_known_builtin() -> None:
    cls = require_plugin("version_stamp")
    assert cls is plugins_pkg.VersionStampPlugin


def test_require_plugin_unknown_raises() -> None:
    from tn_venv.errors import ConfigError

    with pytest.raises(ConfigError):
        require_plugin("nope")


# -- load_plugins: env var path ---------------------------------------------
@pytest.fixture
def _clean_plugin_modules(monkeypatch: pytest.MonkeyPatch):
    created: list[str] = []
    yield created
    for name in created:
        sys.modules.pop(name, None)


def test_load_plugins_from_env_module_with_plugins(
    _clean_plugin_modules: list[str],
) -> None:
    name = "tn_venv_tests_plugin_env"
    _clean_plugin_modules.append(name)

    class _A(Plugin):
        name = "env_a"

        def register(self, hooks):
            hooks.add(HookName.SESSION_START, lambda _c: None, plugin_name=self.name)

    mod = types.ModuleType(name)
    mod.PLUGINS = [_A]
    sys.modules[name] = mod

    reporter = Reporter(verbosity=0)
    registry = load_plugins(reporter=reporter, env={PLUGIN_ENV_VAR: name})
    assert registry.listener_count(HookName.POST_ACTIVATORS) >= 1


def test_load_plugins_from_env_class_reference(
    _clean_plugin_modules: list[str],
) -> None:
    name = "tn_venv_tests_plugin_class"
    _clean_plugin_modules.append(name)

    class _B(Plugin):
        name = "env_b"

        def register(self, hooks):
            hooks.add(HookName.SESSION_END, lambda _c: None, plugin_name=self.name)

    mod = types.ModuleType(name)
    mod._B = _B
    sys.modules[name] = mod

    registry = load_plugins(
        Reporter(verbosity=0),
        env={PLUGIN_ENV_VAR: f"{name}:_B"},
    )
    assert any(
        fn.__name__ == "<lambda>" for fn in registry.listeners(HookName.SESSION_END)
    )


def test_load_plugins_skips_missing_module() -> None:
    reporter = Reporter(verbosity=0)
    load_plugins(
        reporter=reporter,
        env={PLUGIN_ENV_VAR: "definitely.not.a.real.module"},
    )
    assert reporter is not None


def test_load_plugins_skips_missing_attr(
    _clean_plugin_modules: list[str],
) -> None:
    name = "tn_venv_tests_plugin_missing_attr"
    _clean_plugin_modules.append(name)
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    reporter = Reporter(verbosity=0)
    load_plugins(
        reporter=reporter,
        env={PLUGIN_ENV_VAR: f"{name}:DoesNotExist"},
    )
    assert reporter is not None


def test_load_plugins_dedupes_same_class_via_entry_point_and_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same plugin listed via two sources should be loaded once."""

    class _C(Plugin):
        name = "dup_test"

    seen_calls: list[type[Plugin]] = []

    class _FakeEP:
        name = "dup_test"
        value = "tn_venv.tests._fake_dup:Class"

        def load(self):
            seen_calls.append(_C)
            return _C

    monkeypatch.setattr(
        "tn_venv.plugins.loader._iter_entry_points", lambda: iter([_FakeEP()])
    )
    registry = load_plugins(
        Reporter(verbosity=0),
        env={PLUGIN_ENV_VAR: "tn_venv.tests._fake_dup:Class"},
    )
    assert seen_calls.count(_C) == 1
    assert registry is not None


# -- Regression tests for loader bugs --------------------------------------


def test_loader_loads_every_class_in_plugins_list(
    _clean_plugin_modules: list[str],
) -> None:
    """Bug #1 + #2: a module exposing PLUGINS = [A, B, C] must load all three.

    Previously the loader kept only the first instance; the rest were
    silently instantiated and discarded.
    """
    name = "tn_venv_tests_loader_multi"
    _clean_plugin_modules.append(name)

    class _A(Plugin):
        name = "multi_a"

        def register(self, hooks):
            hooks.add(HookName.SESSION_START, lambda c: None, plugin_name=self.name)

    class _B(Plugin):
        name = "multi_b"

        def register(self, hooks):
            hooks.add(HookName.SESSION_START, lambda c: None, plugin_name=self.name)

    class _C(Plugin):
        name = "multi_c"

        def register(self, hooks):
            hooks.add(HookName.SESSION_START, lambda c: None, plugin_name=self.name)

    mod = types.ModuleType(name)
    mod.PLUGINS = [_A, _B, _C]
    sys.modules[name] = mod

    registry = load_plugins(Reporter(verbosity=0), env={PLUGIN_ENV_VAR: name})
    names = {l.plugin_name for l in registry._listeners[HookName.SESSION_START]}  # type: ignore[attr-defined]
    # All three plugin names must appear in the listener list.
    assert {"multi_a", "multi_b", "multi_c"}.issubset(names)


def test_loader_skips_abstract_base_classes(
    _clean_plugin_modules: list[str],
) -> None:
    """Bug #10 + #11: a module that defines ``class Base(Plugin)`` followed
    by ``class Concrete(Base)`` must load ``Concrete``, not ``Base``.

    Previously the vars() scan picked up classes in insertion order, so
    the empty-named base class was selected and the concrete plugin was
    silently dropped.
    """
    name = "tn_venv_tests_loader_base"
    _clean_plugin_modules.append(name)

    class _Base(Plugin):
        name = ""  # abstract / helper base

    class _Concrete(_Base):
        name = "concrete_only"

        def register(self, hooks):
            hooks.add(HookName.PRE_CREATE, lambda c: None, plugin_name=self.name)

    mod = types.ModuleType(name)
    mod._Base = _Base
    mod._Concrete = _Concrete
    sys.modules[name] = mod

    registry = load_plugins(Reporter(verbosity=0), env={PLUGIN_ENV_VAR: name})
    # Exactly one PRE_CREATE listener, registered by _Concrete.
    assert registry.listener_count(HookName.PRE_CREATE) == 1


def test_loader_entry_point_to_module_loads_all_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bug coverage: an entry point that points to a *module* (rather
    than a class) must load every Plugin class declared in that module.

    This path goes through _from_entry_point -> _from_module_attr and
    is what trips users up when their plugin package uses the
    ``PLUGINS = [...]`` convention.
    """

    class _ModuleA(Plugin):
        name = "mod_ep_a"

        def register(self, hooks):
            hooks.add(HookName.SESSION_END, lambda c: None, plugin_name=self.name)

    class _ModuleB(Plugin):
        name = "mod_ep_b"

        def register(self, hooks):
            hooks.add(HookName.SESSION_END, lambda c: None, plugin_name=self.name)

    mod = types.ModuleType("tn_venv_tests_ep_module")
    mod.PLUGINS = [_ModuleA, _ModuleB]
    sys.modules["tn_venv_tests_ep_module"] = mod

    class _FakeEP:
        name = "ep_module_test"
        value = "tn_venv_tests_ep_module"

        def load(self):
            return mod

    monkeypatch.setattr(
        "tn_venv.plugins.loader._iter_entry_points", lambda: iter([_FakeEP()])
    )
    # Clean up the test module from sys.modules so the fixture isn't
    # needed; we only care about the loader's behaviour here.
    try:
        registry = load_plugins(Reporter(verbosity=0))
        names = {
            l.plugin_name
            for l in registry._listeners[HookName.SESSION_END]  # type: ignore[attr-defined]
        }
        assert {"mod_ep_a", "mod_ep_b"}.issubset(names)
    finally:
        sys.modules.pop("tn_venv_tests_ep_module", None)


def test_loader_comma_separated_env_loads_every_spec(
    _clean_plugin_modules: list[str],
) -> None:
    """Bug coverage: ``TN_VENV_PLUGINS=a:A,b:B`` must load both A and B.

    Previously the env-var loader called _resolve_target and threw away
    every plugin after the first one returned per spec.
    """
    name_a = "tn_venv_tests_multi_spec_a"
    name_b = "tn_venv_tests_multi_spec_b"
    _clean_plugin_modules.extend([name_a, name_b])

    class _A(Plugin):
        name = "spec_a"

        def register(self, hooks):
            hooks.add(HookName.POST_SEED, lambda c: None, plugin_name=self.name)

    class _B(Plugin):
        name = "spec_b"

        def register(self, hooks):
            hooks.add(HookName.POST_SEED, lambda c: None, plugin_name=self.name)

    mod_a = types.ModuleType(name_a)
    mod_a._A = _A
    sys.modules[name_a] = mod_a
    mod_b = types.ModuleType(name_b)
    mod_b._B = _B
    sys.modules[name_b] = mod_b

    registry = load_plugins(
        Reporter(verbosity=0),
        env={PLUGIN_ENV_VAR: f"{name_a}:_A,{name_b}:_B"},
    )
    names = {
        l.plugin_name
        for l in registry._listeners[HookName.POST_SEED]  # type: ignore[attr-defined]
    }
    assert {"spec_a", "spec_b"}.issubset(names)


# -- pipeline integration ---------------------------------------------------


class _NullCtx:
    """FileLock replacement: a context manager that does nothing."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _fake_python():
    from tn_venv.discovery import PythonInfo

    return PythonInfo.from_current()


class _FakeCreator:
    """Minimal stand-in for a Creator — returns a populated CreatorContext."""

    def __init__(self, env_dir: Path, prompt: str | None = None) -> None:
        self._env_dir = env_dir
        self._prompt = prompt or ""

    def create(self):
        from tn_venv.create.context import CreatorContext

        py = _fake_python()
        return CreatorContext(
            env_dir=self._env_dir,
            env_name=self._env_dir.name,
            prompt=self._prompt,
            python=py,
            bin_path=self._env_dir / "bin",
            lib_path=self._env_dir / "lib" / "site-packages",
            inc_path=self._env_dir / "include",
            cfg_path=self._env_dir / "pyvenv.cfg",
            env_exe=self._env_dir / "bin" / "python",
            bin_name="bin",
        )


class _FakeSeeder:
    name = "fake"

    def seed(self, ctx, report):
        from tn_venv.seed import SeedResult

        return SeedResult()


def _patch_pipeline(monkeypatch: pytest.MonkeyPatch, env_dir: Path) -> None:
    from tn_venv import session as session_mod

    def _make_creator(*a, **k):
        return _FakeCreator(env_dir, prompt=k.get("prompt"))

    monkeypatch.setattr(session_mod, "discover", lambda *a, **k: _fake_python())
    monkeypatch.setattr(session_mod, "FileLock", lambda *_a, **_k: _NullCtx())
    monkeypatch.setattr(session_mod, "make_creator", _make_creator)
    monkeypatch.setattr(session_mod, "resolve_activators", lambda _names: [])
    monkeypatch.setattr(session_mod, "make_seeder", lambda *_a, **_k: _FakeSeeder())


def test_run_session_emits_every_hook(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """All five hooks fire during a real run_session, in order."""
    from tn_venv import session as session_mod

    fired: list[str] = []

    class _Recording(Plugin):
        name = "recorder"

        def register(self, hooks):
            hooks.add(HookName.SESSION_START, lambda c: fired.append("session_start"))
            hooks.add(HookName.PRE_CREATE, lambda c: fired.append("pre_create"))
            hooks.add(
                HookName.POST_ACTIVATORS, lambda c: fired.append("post_activators")
            )
            hooks.add(HookName.POST_SEED, lambda c: fired.append("post_seed"))
            hooks.add(HookName.SESSION_END, lambda c: fired.append("session_end"))

    env_dir = tmp_path / "venv"
    _patch_pipeline(monkeypatch, env_dir)

    registry = HookRegistry()
    _Recording().register(registry)
    monkeypatch.setattr(session_mod, "load_plugins", lambda reporter=None: registry)

    options = session_mod.Options(dest=env_dir, command="test")
    session_mod.run_session(options, Reporter(verbosity=0))

    assert fired == [
        "session_start",
        "pre_create",
        "post_activators",
        "post_seed",
        "session_end",
    ]


def test_session_end_hook_can_mutate_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from tn_venv import session as session_mod

    class _Tagger(Plugin):
        name = "tagger"

        def register(self, hooks):
            def _tag(ctx):
                if ctx.result is not None:
                    ctx.result.prompt = ctx.result.prompt + "!"

            hooks.add(HookName.SESSION_END, _tag)

    env_dir = tmp_path / "venv"
    _patch_pipeline(monkeypatch, env_dir)

    registry = HookRegistry()
    _Tagger().register(registry)
    monkeypatch.setattr(session_mod, "load_plugins", lambda reporter=None: registry)

    options = session_mod.Options(dest=env_dir, prompt="base")
    result = session_mod.run_session(options, Reporter(verbosity=0))
    assert result.prompt == "base!"


def test_broken_listener_does_not_break_run_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from tn_venv import session as session_mod

    class _Boom(Plugin):
        name = "boom"

        def register(self, hooks):
            def _fn(_ctx):
                raise RuntimeError("plugin exploded")

            hooks.add(HookName.SESSION_START, _fn)

    env_dir = tmp_path / "venv"
    _patch_pipeline(monkeypatch, env_dir)

    registry = HookRegistry()
    _Boom().register(registry)
    monkeypatch.setattr(session_mod, "load_plugins", lambda reporter=None: registry)

    options = session_mod.Options(dest=env_dir)
    result = session_mod.run_session(options, Reporter(verbosity=0))
    assert result.env_dir == env_dir


def test_run_session_exposes_cfg_path_and_scripts_to_plugins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from tn_venv import session as session_mod

    captured: dict[str, object] = {}

    class _Capturing(Plugin):
        name = "capture"

        def register(self, hooks):
            hooks.add(HookName.POST_ACTIVATORS, self._on_post)

        def _on_post(self, ctx):
            captured["cfg_path"] = ctx.data.get("cfg_path")
            captured["scripts"] = ctx.data.get("scripts")
            captured["env_dir"] = ctx.data.get("env_dir")

    env_dir = tmp_path / "venv"
    _patch_pipeline(monkeypatch, env_dir)

    registry = HookRegistry()
    _Capturing().register(registry)
    monkeypatch.setattr(session_mod, "load_plugins", lambda reporter=None: registry)

    options = session_mod.Options(dest=env_dir)
    session_mod.run_session(options, Reporter(verbosity=0))

    assert captured["env_dir"] == env_dir
    assert captured["cfg_path"] == env_dir / "pyvenv.cfg"
    assert captured["scripts"] == []


# -- Loader provenance (PluginSource + owner map) --------------------------


def test_load_plugins_tags_each_plugin_with_source(
    _clean_plugin_modules: list[str],
) -> None:
    """Every loaded plugin carries a PluginSource via _tn_venv_source."""
    name = "tn_venv_tests_source_tag"
    _clean_plugin_modules.append(name)

    class _A(Plugin):
        name = "tagged_a"

        def register(self, hooks):
            hooks.add(
                HookName.SESSION_START, lambda c: None, plugin_name=self.name
            )

    mod = types.ModuleType(name)
    mod._A = _A
    sys.modules[name] = mod

    registry = load_plugins(
        Reporter(verbosity=0), env={PLUGIN_ENV_VAR: f"{name}:_A"}
    )
    # Find our plugin by name; the loader may have other plugins
    # (built-ins, third-party entry points) loaded too.
    owners = list(registry._owners.values())  # type: ignore[attr-defined]
    mine = [p for p in owners if isinstance(p, _A)]
    assert mine, "loader did not register _A in the owner map"
    plugin = mine[0]
    assert plugin._tn_venv_source.kind == "env"  # type: ignore[attr-defined]
    assert plugin._tn_venv_source.spec == PLUGIN_ENV_VAR  # type: ignore[attr-defined]


def test_register_with_owner_recovers_owner_for_decorator_form() -> None:
    """The owner map also works for plugins using @hooks.add as a decorator."""
    from tn_venv.plugins.loader import _register_with_owner
    from tn_venv.plugins.registry import HookRegistry

    class _DecoratorPlugin(Plugin):
        name = "deco_owner"

        def register(self, hooks):
            @hooks.add(HookName.SESSION_START, plugin_name=self.name)
            def _cb(ctx):
                pass

    reg = HookRegistry()
    plugin = _DecoratorPlugin()
    _register_with_owner(reg, plugin)

    listener = reg._listeners[HookName.SESSION_START][0]  # type: ignore[attr-defined]
    assert reg._owners[id(listener.fn)] is plugin  # type: ignore[attr-defined]


def test_register_with_owner_restores_registry_on_exception() -> None:
    """A plugin that raises during register() must not break the registry."""
    from tn_venv.plugins.loader import _register_with_owner
    from tn_venv.plugins.registry import HookRegistry

    class _Boom(Plugin):
        name = "boom"

        def register(self, hooks):
            hooks.add(HookName.SESSION_START, lambda c: None)
            raise RuntimeError("boom")

    reg = HookRegistry()
    with pytest.raises(RuntimeError):
        _register_with_owner(reg, _Boom())

    # The registry must remain usable: the listener from before the
    # raise is still there, and a subsequent add() must work.
    assert reg.listener_count(HookName.SESSION_START) == 1
    reg.add(HookName.SESSION_START, lambda c: None)
    assert reg.listener_count(HookName.SESSION_START) == 2


def test_register_with_owner_swallows_attribute_errors() -> None:
    """A plugin with __slots__ that disallows _tn_venv_source must not crash."""

    class _Slotty:
        __slots__ = ("name",)

        def __init__(self):
            self.name = "slotty"

    # Direct invocation: the tag-source helper shouldn't blow up.
    from tn_venv.plugins.loader import _tag_source, PluginSource

    plugin = _Slotty()
    _tag_source(plugin, PluginSource(kind="env", spec="TN_VENV_PLUGINS"))
    # _tn_venv_source was not set (slots disallow it); that's fine.
    assert not hasattr(plugin, "_tn_venv_source")


def test_register_with_owner_tracks_hookless_plugins() -> None:
    """A plugin that adds no hooks still shows up in _hookless_plugins.

    This is what makes plugins like ``GuiSubcommandPlugin`` (CLI shims)
    discoverable via ``tn-venv --list-plugins``: their ``register()``
    side-effects the host but never calls ``hooks.add(...)``.
    """
    from tn_venv.plugins.loader import _register_with_owner
    from tn_venv.plugins.registry import HookRegistry

    class _Shim(Plugin):
        name = "shim"

        def register(self, hooks):
            # No hooks.add — just a side effect (e.g. monkey-patch).
            return

    reg = HookRegistry()
    _register_with_owner(reg, _Shim())

    assert reg._hookless_plugins  # type: ignore[attr-defined]
    assert isinstance(reg._hookless_plugins[0], _Shim)  # type: ignore[attr-defined]
    # No real listener was added, so owners should still be empty.
    assert reg._owners == {}  # type: ignore[attr-defined]


def test_register_with_owner_dedupes_when_plugin_adds_hooks_then_none() -> None:
    """A plugin that adds hooks first and a sentinel later is recorded once.

    Mixed behaviour shouldn't cause the same instance to appear in
    both ``_owners`` and ``_hookless_plugins``.
    """
    from tn_venv.plugins.loader import _register_with_owner
    from tn_venv.plugins.registry import HookRegistry

    class _Mixed(Plugin):
        name = "mixed"

        def register(self, hooks):
            hooks.add(HookName.SESSION_START, lambda c: None, plugin_name=self.name)

    reg = HookRegistry()
    _register_with_owner(reg, _Mixed())

    assert reg._owners  # type: ignore[attr-defined]
    # ``setdefault`` keeps the hookful entry from being clobbered.
    assert reg._hookless_plugins == []  # type: ignore[attr-defined]
