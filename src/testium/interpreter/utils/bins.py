"""Centralised resolution of external interpreter paths (Python, Lua).

The user can override the path through the global dict via the keys
``python_bin`` and ``lua_bin`` (typically populated from a YAML config).
When unset, the system PATH is searched for known candidates.

Resolution is cached in memory: each interpreter is resolved at most
once per testium process. Subsequent calls return the cached value.

Public API
----------
``python_bin()``        : resolved python3 path (or "" if missing)
``lua_bin()``           : resolved lua >= 5.1 path (or "" if missing)
``ensure(*names)``      : resolve every name and raise a clear error if
                          any is missing — meant for early validation at
                          test load time
``reset()``             : clear the cache (mostly useful for tests)
"""

import shutil
import subprocess

import api.testium as tm
from interpreter.utils.paths import sys_app_path_lin, sys_app_path_win
from runtime.tum_except import ETUMRuntimeError


# ---------- Discovery primitives ---------------------------------------------

_PYTHON_CANDIDATES = ["python3", "python"]
_LUA_CANDIDATES = ["lua", "lua5.5", "lua5.4", "lua5.3", "lua5.2", "lua5.1"]


def _which(name):
    func = sys_app_path_win if tm.OS() == "Windows" else sys_app_path_lin
    return func(name)


def _python_version(path):
    cmd = [path, "-c", "import sys; print(sys.version_info[:3])"]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding=tm.sys_encoding(), timeout=10,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return None
    try:
        return eval(r.stdout)
    except Exception:
        return None


def _is_python3(path):
    v = _python_version(path)
    return v is not None and v[0] == 3


def _lua_version(path):
    try:
        r = subprocess.run(
            [path, "-v"], capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return None
    # On Windows the version banner goes to stderr.
    line = r.stdout or r.stderr
    try:
        major, minor, _patch = line.split(" ")[1].split(".")
        return (int(major), int(minor))
    except (IndexError, ValueError):
        return None


def _is_lua51(path):
    v = _lua_version(path)
    return v is not None and v >= (5, 1)


# ---------- Resolver ---------------------------------------------------------

# (display name, globdict override key, candidate list, validator)
_SPECS = {
    "python": ("Python 3", "python_bin", _PYTHON_CANDIDATES, _is_python3),
    "lua":    ("Lua 5.1+",  "lua_bin",    _LUA_CANDIDATES,    _is_lua51),
}

_resolved = {}


def _resolve(name):
    if name in _resolved:
        return _resolved[name]

    display, gd_key, candidates, validator = _SPECS[name]
    override = tm.gd(gd_key, "") or ""

    path = ""
    if override:
        if shutil.which(override) and validator(override):
            path = override
        else:
            tm.print_warn(
                f"Configured {display} interpreter '{override}' is not usable; "
                f"falling back to discovery."
            )

    if not path:
        for c in candidates:
            p = _which(c)
            if not p:
                continue
            if validator(p):
                path = p
                break

    _resolved[name] = path
    return path


def python_bin():
    return _resolve("python")


def lua_bin():
    return _resolve("lua")


def ensure(*names):
    """Resolve each of the given names; raise if any is missing.

    Meant to be called at test load with the set of interpreters the
    test tree actually needs, so the user gets a clear error before
    execution starts instead of deep inside an engine spawn.
    """
    missing = []
    for n in names:
        if not _resolve(n):
            display, gd_key, candidates, _ = _SPECS[n]
            missing.append(
                f"  - {display}: tried {candidates} on PATH, none usable. "
                f"Set '{gd_key}' in the YAML config to override."
            )
    if missing:
        raise ETUMRuntimeError(
            "Required external interpreter(s) not found:\n" + "\n".join(missing)
        )


def reset():
    _resolved.clear()
