"""Tests for tn_venv.config.spec — option declarations and value coercion."""

from __future__ import annotations

import pytest

from tn_venv.config.spec import OPTION_SPECS, OptionSpec, coerce_value
from tn_venv.errors import ConfigError


def _spec(dest: str, **overrides) -> OptionSpec:
    spec = OPTION_SPECS[dest]
    return OptionSpec(**{**spec.__dict__, **overrides})


def test_all_specs_have_dest() -> None:
    assert all(s.dest for s in OPTION_SPECS.values())


def test_all_specs_have_unique_dest() -> None:
    dests = [s.dest for s in OPTION_SPECS.values()]
    assert len(dests) == len(set(dests))


def test_python_spec_is_append() -> None:
    assert OPTION_SPECS["python"].kind == "append"


def test_pip_spec_optional_str() -> None:
    spec = OPTION_SPECS["pip"]
    assert spec.kind == "optional_str"
    assert spec.optional_const == "latest"


def test_env_name_default_uppercase() -> None:
    spec = OptionSpec(dest="foo_bar")
    assert spec.env_name == "TN_VENV_FOO_BAR"


def test_env_name_explicit_override() -> None:
    spec = OptionSpec(dest="foo", env="CUSTOM_ENV")
    assert spec.env_name == "CUSTOM_ENV"


def test_config_key_is_kebab() -> None:
    spec = OptionSpec(dest="extra_search_dir")
    assert spec.config_key == "extra-search-dir"


@pytest.mark.parametrize(
    "true_value", ["1", "true", "yes", "on", "y", "t", "TRUE", "Yes"]
)
def test_coerce_bool_truthy(true_value: str) -> None:
    spec = OPTION_SPECS["clear"]
    assert coerce_value(spec, true_value) is True


@pytest.mark.parametrize(
    "false_value", ["0", "false", "no", "off", "n", "f", "", "FALSE"]
)
def test_coerce_bool_falsey(false_value: str) -> None:
    spec = OPTION_SPECS["clear"]
    assert coerce_value(spec, false_value) is False


def test_coerce_bool_passthrough_bool() -> None:
    spec = OPTION_SPECS["clear"]
    assert coerce_value(spec, True) is True
    assert coerce_value(spec, False) is False


def test_coerce_bool_invalid_raises() -> None:
    spec = OPTION_SPECS["clear"]
    with pytest.raises(ConfigError):
        coerce_value(spec, "maybe")


def test_coerce_int() -> None:
    spec = OptionSpec(dest="x", kind="int")
    assert coerce_value(spec, "42") == 42


def test_coerce_count() -> None:
    spec = OptionSpec(dest="x", kind="count")
    assert coerce_value(spec, "3") == 3


def test_coerce_append_csv_string() -> None:
    spec = OPTION_SPECS["python"]
    assert coerce_value(spec, "3.12,3.13") == ["3.12", "3.13"]


def test_coerce_append_passthrough_list() -> None:
    spec = OPTION_SPECS["python"]
    assert coerce_value(spec, ["3.12", "3.13"]) == ["3.12", "3.13"]


def test_coerce_optional_str_bool_true_uses_const() -> None:
    spec = OPTION_SPECS["pip"]
    # The argparse layer sends a string; from env we get bool-ish strings.
    # When a bool True is passed via Python, it resolves to the const.
    assert coerce_value(spec, True) == "latest"


def test_coerce_optional_str_passthrough_string() -> None:
    spec = OPTION_SPECS["pip"]
    assert coerce_value(spec, "24.0") == "24.0"


def test_coerce_choices_rejects_invalid() -> None:
    spec = OPTION_SPECS["seeder"]
    with pytest.raises(ConfigError):
        coerce_value(spec, "bogus")


def test_coerce_choices_accepts_valid() -> None:
    spec = OPTION_SPECS["seeder"]
    assert coerce_value(spec, "none") == "none"


def test_coerce_none_returns_none() -> None:
    spec = OPTION_SPECS["clear"]
    assert coerce_value(spec, None) is None


def test_coerce_int_invalid_raises() -> None:
    spec = OptionSpec(dest="x", kind="int")
    with pytest.raises(ConfigError):
        coerce_value(spec, "notanumber")


def test_coerce_plain_str() -> None:
    spec = OPTION_SPECS["prompt"]
    assert coerce_value(spec, "myproj") == "myproj"
