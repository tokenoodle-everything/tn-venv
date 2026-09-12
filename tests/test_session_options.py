"""Tests for tn_venv.session: Options + merge_config."""

from __future__ import annotations

import pytest

from tn_venv.config.spec import OPTION_SPECS
from tn_venv.errors import ConfigError
from tn_venv.session import HARD_DEFAULTS, Options, merge_config


def test_options_defaults_match_spec_defaults() -> None:
    opts = Options()
    for spec in OPTION_SPECS.values():
        # Options only carries non-cli-only fields.
        if spec.cli_only:
            continue
        if spec.kind == "append":
            assert getattr(opts, spec.dest) == []
        elif spec.kind == "count":
            # count kinds (quiet, verbose) default to 0, not spec.default
            assert getattr(opts, spec.dest) == 0
        else:
            assert getattr(opts, spec.dest) == spec.default


def test_options_use_symlinks_default_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("os.name", "posix", raising=False)
    assert Options().use_symlinks is True


def test_options_use_symlinks_default_nt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("os.name", "nt", raising=False)
    assert Options().use_symlinks is False


def test_options_use_symlinks_explicit() -> None:
    assert Options(symlinks=True, copies=False).use_symlinks is True
    assert Options(symlinks=False, copies=True).use_symlinks is False


def test_options_use_symlinks_conflict_raises() -> None:
    with pytest.raises(ConfigError):
        _ = Options(symlinks=True, copies=True).use_symlinks


def test_options_verbosity_calculation() -> None:
    assert Options().verbosity == 1
    assert Options(verbose=1).verbosity == 2
    assert Options(verbose=3).verbosity == 3
    assert Options(quiet=1).verbosity == 0
    assert Options(verbose=2, quiet=1).verbosity == 2


def test_options_verbosity_clamped() -> None:
    assert Options(verbose=99).verbosity == 3
    assert Options(quiet=99).verbosity == 0


def test_options_wants_pip_default_true() -> None:
    assert Options().wants_pip is True


def test_options_wants_pip_disabled_by_no_pip() -> None:
    assert Options(no_pip=True).wants_pip is False


def test_options_wants_pip_disabled_by_seeder_none() -> None:
    assert Options(seeder="none").wants_pip is False


def test_options_from_mapping_normalises_lists() -> None:
    opts = Options.from_mapping({"python": ["3.12"], "extra_search_dir": ["/x"]})
    assert opts.python == ["3.12"]
    assert opts.extra_search_dir == ["/x"]


def test_options_from_mapping_ignores_unknown() -> None:
    opts = Options.from_mapping({"python": ["3.12"], "unknown": "value"})
    assert not hasattr(opts, "unknown")


def test_options_from_mapping_drops_none() -> None:
    opts = Options.from_mapping({"prompt": None, "python": ["3"]})
    assert opts.prompt is None


def test_merge_config_defaults_only() -> None:
    assert merge_config({}) == HARD_DEFAULTS


def test_merge_config_cli_overrides_env() -> None:
    out = merge_config({"clear": True}, {"clear": False})
    assert out["clear"] is True


def test_merge_config_env_overrides_file() -> None:
    out = merge_config({}, {"clear": True}, {"clear": False})
    assert out["clear"] is True


def test_merge_config_file_overrides_default() -> None:
    out = merge_config({}, {}, {"clear": True})
    assert out["clear"] is True


def test_merge_config_skips_none() -> None:
    out = merge_config({"clear": None})
    assert out["clear"] == HARD_DEFAULTS["clear"]


def test_merge_config_none_layers_safe() -> None:
    assert merge_config({}, None, None) == HARD_DEFAULTS
