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

import os
import subprocess

import api.testium as tm
from interpreter.utils.paths import sys_app_path_lin, sys_app_path_win
from runtime.tum_except import ETUMRuntimeError


# ---------- Discovery primitives ---------------------------------------------

_PYTHON_CANDIDATES = ["python3", "python"]
_LUA_CANDIDATES = ["lua", "lua5.5", "lua5.4", "lua5.3", "lua5.2", "lua5.1"]

# When running inside a Flatpak, --filesystem=host-os mounts the host at
# /run/host (read-only). Binaries and libraries from the host are not on the
# sandbox PATH/LD_LIBRARY_PATH, so we probe and inject them explicitly.
_FLATPAK_HOST_DIRS = [
    "/run/host/usr/local/bin",
    "/run/host/usr/bin",
    "/run/host/bin",
]
_FLATPAK_HOST_LIB_DIRS = [
    "/run/host/usr/lib",
    "/run/host/usr/lib64",
    "/run/host/usr/local/lib",
]

# Inside an AppImage, AppRun prepends $APPDIR/usr/bin to PATH and exports a
# bundle-local PYTHONHOME / PYTHONPATH / LD_LIBRARY_PATH. We want py_func and
# lua_func to run under the *host* interpreter (not the bundled one), so we
# probe standard host bin dirs directly and scrub APPDIR-prefixed entries from
# the env passed to host subprocesses.
_APPIMAGE_HOST_DIRS = [
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
]


def _in_flatpak():
    return os.path.isfile("/.flatpak-info")


def _in_appimage():
    return "APPIMAGE" in os.environ


def apply_host_lua_paths(env):
    """Prepend host Lua module dirs to LUA_PATH / LUA_CPATH (Flatpak only).

    Must be called after user-defined lua_env overrides are applied, so host
    paths are always first regardless of user config. User-defined paths remain
    in the variable but after the host ones.
    """
    if not _in_flatpak():
        return
    _LUA_VERSIONS = ["5.5", "5.4", "5.3", "5.2", "5.1"]
    _HOST = "/run/host/usr"
    cpath_dirs, lpath_dirs = [], []
    for v in _LUA_VERSIONS:
        for base in [f"{_HOST}/lib/lua/{v}",
                     f"{_HOST}/lib64/lua/{v}",
                     f"{_HOST}/lib/x86_64-linux-gnu/lua/{v}"]:
            cpath_dirs.append(f"{base}/?.so")
        lpath_dirs.append(f"{_HOST}/share/lua/{v}/?.lua")
        lpath_dirs.append(f"{_HOST}/share/lua/{v}/?/init.lua")
    sep = ";"
    host_cpath = sep.join(cpath_dirs)
    host_lpath = sep.join(lpath_dirs)
    # ;; keeps Lua's compiled-in defaults at the end as last resort
    env["LUA_CPATH"] = host_cpath + sep + env.get("LUA_CPATH", ";;")
    env["LUA_PATH"]  = host_lpath + sep + env.get("LUA_PATH",  ";;")


def apply_host_libs(env):
    """Prepare *env* for launching a host binary from inside our bundle.

    - Flatpak: prepend host library dirs to LD_LIBRARY_PATH so the dynamic
      linker can find host .so files mounted under /run/host.
    - AppImage: strip $APPDIR-prefixed entries from LD_LIBRARY_PATH and
      PYTHONPATH and drop PYTHONHOME, so the host interpreter doesn't try
      to load the bundled (incompatible) Python lib/site-packages.
    - Otherwise: no-op.
    """
    if _in_flatpak():
        dirs = ":".join(d for d in _FLATPAK_HOST_LIB_DIRS if os.path.isdir(d))
        if dirs:
            existing = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = dirs + (":" + existing if existing else "")
        return
    if _in_appimage():
        appdir = os.environ.get("APPDIR", "")
        if appdir:
            for var, sep in (("LD_LIBRARY_PATH", ":"),
                             ("PYTHONPATH", os.pathsep),
                             ("PATH", os.pathsep)):
                cur = env.get(var, "")
                if not cur:
                    continue
                cleaned = sep.join(
                    p for p in cur.split(sep)
                    if p and not p.startswith(appdir)
                )
                if cleaned:
                    env[var] = cleaned
                else:
                    env.pop(var, None)
        env.pop("PYTHONHOME", None)


def _which(name):
    if tm.OS() == "Windows":
        return sys_app_path_win(name)
    if _in_flatpak():
        for d in _FLATPAK_HOST_DIRS:
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return ""
    if _in_appimage():
        for d in _APPIMAGE_HOST_DIRS:
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return ""
    return sys_app_path_lin(name)


def _probe_env():
    """Subprocess env for probing host binaries (adds host libs in Flatpak)."""
    env = os.environ.copy()
    apply_host_libs(env)
    return env


def _python_version(path):
    cmd = [path, "-c", "import sys; print(sys.version_info[:3])"]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding=tm.sys_encoding(), timeout=10, env=_probe_env(),
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
            env=_probe_env(),
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

# Cached per (name, override) so that runtime changes to gd[gd_key] —
# e.g. ``python_bin`` set from a YAML config file loaded *after*
# eval_proc has already resolved its own interpreter — are picked up by
# the next lookup instead of returning the stale, auto-discovered path.
# Long-lived subprocesses (eval_proc) keep whatever they captured at
# construction time, but every new PyProcessBase / FuncExecEngine spawned
# afterwards sees the current override.
_resolved = {}


def _resolve(name):
    display, gd_key, candidates, validator = _SPECS[name]
    override = tm.gd(gd_key, "") or ""

    cached = _resolved.get(name)
    if cached is not None and cached[0] == override:
        return cached[1]

    path = ""
    if override:
        # Absolute path: accept as-is (user knows exactly what they want).
        # Bare name: resolve via _which() so the override stays host-only in
        # Flatpak/AppImage instead of silently picking the bundled interpreter.
        if os.path.isabs(override):
            resolved = override if (os.path.isfile(override)
                                    and os.access(override, os.X_OK)) else ""
        else:
            resolved = _which(override)
        if resolved and validator(resolved):
            path = resolved
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

    _resolved[name] = (override, path)
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
