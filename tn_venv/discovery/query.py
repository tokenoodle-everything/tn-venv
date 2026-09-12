"""The probe script executed inside candidate interpreters.

It prints a single line of JSON describing the interpreter so tn-venv can
decide version matching and locate the binaries / venv launchers to copy.
Runs with ``-I`` (isolated mode) for determinism.
"""

from __future__ import annotations

QUERY_SCRIPT = r"""
import json, os, struct, sys

def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default

def _sysconfig():
    import sysconfig
    def _var(name):
        try:
            return sysconfig.get_config_var(name)
        except Exception:
            return None
    def _is_build():
        try:
            return bool(sysconfig.is_python_build())
        except Exception:
            return False
    return {
        "gil_disabled": bool(_var("Py_GIL_DISABLED")),
        "is_python_build": _is_build(),
        "abiflags": _var("ABIFLAGS") or "",
        "libdir": _var("LIBDIR"),
        "ldlibrary": _var("LDLIBRARY"),
        "stdlib": _var("stdlib") or _safe(lambda: os.path.dirname(os.__file__)),
    }

def _scripts_nt(stdlib):
    if os.name != "nt" or not stdlib:
        return None
    cand = os.path.join(stdlib, "venv", "scripts", "nt")
    return cand if os.path.isdir(cand) else None

def _site():
    try:
        import site
        return {
            "purelib": _safe(lambda: site.getsitepackages()[0]),
        }
    except Exception:
        return {"purelib": None}

_sc = _sysconfig()
_base_exe = getattr(sys, "_base_executable", None) or sys.executable
data = {
    "executable": os.path.abspath(sys.executable),
    "base_executable": os.path.abspath(_base_exe) if _base_exe else None,
    "version_info": list(sys.version_info[:3]),
    "version": sys.version.split()[0],
    "implementation": getattr(sys.implementation, "name", "cpython"),
    "prefix": sys.prefix,
    "base_prefix": getattr(sys, "base_prefix", sys.prefix),
    "exec_prefix": sys.exec_prefix,
    "base_exec_prefix": getattr(sys, "base_exec_prefix", sys.exec_prefix),
    "maxsize": sys.maxsize,
    "bits": struct.calcsize("P") * 8,
    "machine": _safe(lambda: __import__("platform").machine(), ""),
    "stdlib": _sc["stdlib"],
    "scripts_nt": _scripts_nt(_sc["stdlib"]),
    "gil_disabled": _sc["gil_disabled"],
    "is_python_build": _sc["is_python_build"],
    "abiflags": _sc["abiflags"],
    "libdir": _sc["libdir"],
    "ldlibrary": _sc["ldlibrary"],
    "site": _site(),
}
print("__TN_VENV_INFO__" + json.dumps(data))
"""

MARKER = "__TN_VENV_INFO__"
