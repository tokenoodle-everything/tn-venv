"""Activator registry."""

from __future__ import annotations

from .base import Activator
from .bash import BashActivator
from .batch import BatchActivator
from .csh import CShActivator
from .fish import FishActivator
from .nushell import NushellActivator
from .powershell import PowerShellActivator
from .python_activate import PythonActivator

_ALL: dict[str, type[Activator]] = {
    cls.name: cls
    for cls in (
        BashActivator,
        BatchActivator,
        PowerShellActivator,
        FishActivator,
        CShActivator,
        NushellActivator,
        PythonActivator,
    )
}

DEFAULT_ACTIVATORS = tuple(_ALL)

__all__ = [
    "Activator",
    "available_activators",
    "resolve_activators",
    "DEFAULT_ACTIVATORS",
]


def available_activators() -> list[str]:
    return sorted(_ALL)


def resolve_activators(names: list[str] | None) -> list[Activator]:
    """Turn a user selection into activator instances.

    ``None``/``["default"]`` → the full default set; ``["all"]`` → everything;
    a leading ``-`` prefix (``-fish``) removes from the default set.
    The ``all`` and ``default`` pseudo-activators may be combined with
    exclusions, e.g. ``["all,-fish"]`` or ``["default,-fish"]``.
    """
    if not names:
        return [cls() for cls in _ALL.values()]
    expanded: list[str] = []
    for chunk in names:
        expanded.extend(part.strip() for part in chunk.split(",") if part.strip())
    if not expanded:
        return [cls() for cls in _ALL.values()]
    removals = [n[1:] for n in expanded if n.startswith("-")]
    raw_additions = [n for n in expanded if not n.startswith("-")]
    # ``all`` / ``default`` are pseudo-activators that mean "every registered
    # activator".  They may appear on their own or alongside exclusions;
    # bare names like ``bash`` and the pseudo-activators do not mix, so we
    # treat any pseudo-token as a request for the full set.
    pseudo = {"all", "default"}
    has_pseudo = any(token in pseudo for token in raw_additions)
    if has_pseudo and raw_additions != [t for t in raw_additions if t in pseudo]:
        # Mixing pseudo-activators with bare names (or with each other in a
        # way that leaves other tokens) is ambiguous; reject.
        from ...errors import ConfigError

        raise ConfigError(
            f"unknown activator(s): {', '.join(raw_additions)}; "
            f"available: {', '.join(available_activators())}"
        )
    # ``all`` / ``default`` (and a bare-removals-only selection) start from
    # the full set; an explicit list of names starts from just those names.
    if has_pseudo or not raw_additions:
        selected = list(_ALL)
    else:
        selected = list(raw_additions)
    for name in removals:
        if name in selected:
            selected.remove(name)
    unknown = [n for n in selected if n not in _ALL]
    if unknown:
        from ...errors import ConfigError

        raise ConfigError(
            f"unknown activator(s): {', '.join(unknown)}; "
            f"available: {', '.join(available_activators())}"
        )
    return [_ALL[name]() for name in selected]
