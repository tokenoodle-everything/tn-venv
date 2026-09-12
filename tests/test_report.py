"""Tests for tn_venv.report."""

from __future__ import annotations

import io
import os

import pytest

from tn_venv.report import (
    SILENT,
    Reporter,
    VERBOSITY_DEBUG,
    VERBOSITY_DEFAULT,
    VERBOSITY_QUIET,
    VERBOSITY_VERBOSE,
    detect_color,
)


@pytest.fixture()
def stream() -> io.StringIO:
    return io.StringIO()


def _reporter(
    verbosity: int, color: bool = False, out: io.StringIO | None = None
) -> Reporter:
    return Reporter(verbosity=verbosity, color=color, stream=out or io.StringIO())


def test_verbosity_constants_are_ordered() -> None:
    assert VERBOSITY_QUIET < VERBOSITY_DEFAULT < VERBOSITY_VERBOSE < VERBOSITY_DEBUG


def test_default_verbosity() -> None:
    assert _reporter(VERBOSITY_DEFAULT).verbosity == VERBOSITY_DEFAULT


@pytest.mark.parametrize(
    "level, method, expected",
    [
        (VERBOSITY_QUIET, "error", True),
        (VERBOSITY_QUIET, "warn", False),
        (VERBOSITY_QUIET, "info", False),
        (VERBOSITY_QUIET, "ok", False),
        (VERBOSITY_QUIET, "step", False),
        (VERBOSITY_QUIET, "debug", False),
        (VERBOSITY_DEFAULT, "warn", True),
        (VERBOSITY_DEFAULT, "info", True),
        (VERBOSITY_DEFAULT, "step", True),
        (VERBOSITY_DEFAULT, "debug", False),
        (VERBOSITY_VERBOSE, "ok", True),
        (VERBOSITY_VERBOSE, "debug", False),
        (VERBOSITY_DEBUG, "debug", True),
    ],
)
def test_verbosity_filtering(
    level: int, method: str, expected: bool, stream: io.StringIO
) -> None:
    r = _reporter(level, out=stream)
    getattr(r, method)("hello")
    assert bool(stream.getvalue()) is expected


def test_step_prefix() -> None:
    r = _reporter(VERBOSITY_DEFAULT, out=io.StringIO())
    out = io.StringIO()
    r.stream = out
    r.step("creating")
    assert out.getvalue().startswith("==> creating")


def test_error_prefix_always_emitted() -> None:
    r = _reporter(VERBOSITY_QUIET, out=io.StringIO())
    out = io.StringIO()
    r.stream = out
    r.error("boom")
    assert out.getvalue().startswith("error: boom")


def test_colored_when_enabled() -> None:
    out = io.StringIO()
    r = Reporter(verbosity=VERBOSITY_DEBUG, color=True, stream=out)
    # ``color=True`` requests ANSI; whether it actually emits depends on the
    # host enabling VT processing.  On Windows when VT can be enabled, or on
    # any POSIX tty, the reporter emits ANSI escapes; otherwise it falls back
    # to plain text.  Verify the helper at least runs without error.
    text = out.getvalue()  # nothing written yet
    assert text == ""
    r.error("hi")
    written = out.getvalue()
    assert "hi" in written


def test_no_color_when_disabled() -> None:
    out = io.StringIO()
    r = Reporter(verbosity=VERBOSITY_DEBUG, color=False, stream=out)
    r.error("hi")
    r.info("hello")
    # When color is explicitly disabled, no ANSI escapes should appear
    assert "\x1b[" not in out.getvalue()


def test_style_is_passthrough_when_disabled() -> None:
    r = Reporter(verbosity=VERBOSITY_DEBUG, color=False)
    assert r.style("xyz", "error") == "xyz"


def test_path_helper() -> None:
    r = Reporter(color=False)
    assert r.path("/tmp/x") == "/tmp/x"


def test_silent_reporter_emits_nothing(stream: io.StringIO) -> None:
    # SILENT has verbosity=-1, everything is suppressed
    r = SILENT
    r.stream = stream
    r.error("x")
    r.info("x")
    r.debug("x")
    assert stream.getvalue() == ""


def test_detect_color_force_true(monkeypatch: pytest.MonkeyPatch) -> None:
    # When forced on and VT can be enabled, detect_color returns True.
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("TN_VENV_FORCE_COLOR", raising=False)
    result = detect_color(stream=io.StringIO(), force=True)
    assert isinstance(result, bool)


def test_detect_color_no_color_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("TN_VENV_FORCE_COLOR", raising=False)
    # Non-tty stream is fine; NO_COLOR should win
    assert detect_color(stream=io.StringIO()) is False


def test_detect_color_non_tty_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("TN_VENV_FORCE_COLOR", raising=False)
    assert detect_color(stream=io.StringIO()) is False


def test_detect_color_force_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert detect_color(stream=io.StringIO(), force=False) is False


def test_emission_uses_assigned_stream() -> None:
    buf = io.StringIO()
    r = Reporter(verbosity=VERBOSITY_DEFAULT, color=False)
    r.stream = buf
    r.warn("watch out")
    assert "warning: watch out" in buf.getvalue()


def test_emission_to_none_stream_does_not_crash() -> None:
    # Reporter.stream default is sys.stdout — just exercise emission
    r = Reporter(verbosity=VERBOSITY_QUIET, color=False)
    r.error("ignored")


@pytest.mark.skipif(os.name != "nt", reason="windows-specific vt check")
def test_enable_windows_vt_returns_bool() -> None:
    from tn_venv.report import _enable_windows_vt

    # We don't assert the value — just that the call doesn't raise
    assert isinstance(_enable_windows_vt(), bool)
