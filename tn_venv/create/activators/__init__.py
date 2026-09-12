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
    """
    if not names or names == ["default"]:
        return [cls() for cls in _ALL.values()]
    expanded: list[str] = []
    for chunk in names:
        expanded.extend(part.strip() for part in chunk.split(",") if part.strip())
    if expanded == ["all"]:
        return [cls() for cls in _ALL.values()]
    removals = [n[1:] for n in expanded if n.startswith("-")]
    additions = [n for n in expanded if not n.startswith("-")]
    selected = list(additions) if additions else list(_ALL)
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
