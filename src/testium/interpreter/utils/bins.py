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

import atexit
import os
import shlex
import shutil
import subprocess
import tempfile

import api.testium as tm
from interpreter.utils.paths import sys_app_path_lin, sys_app_path_win
from runtime.tum_except import ETUMRuntimeError


# ---------- Discovery primitives ---------------------------------------------

_PYTHON_CANDIDATES = ["python3", "python"]
_LUA_CANDIDATES = ["lua", "lua5.5", "lua5.4", "lua5.3", "lua5.2", "lua5.1"]

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


def apply_host_libs(env):
    """Strip bundle-local entries from *env* so a host binary can run cleanly.

    Only meaningful for AppImage: removes $APPDIR-prefixed entries from
    LD_LIBRARY_PATH / PYTHONPATH / PATH and drops PYTHONHOME, so the host
    interpreter doesn't try to load the bundled (incompatible) Python
    lib/site-packages. Flatpak is handled via flatpak-spawn --host instead
    (see flatpak_host_spawn), so the sandbox env is irrelevant there.
    """
    if not _in_appimage():
        return
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


# ---------- Flatpak: spawn on host outside the sandbox -----------------------
#
# Inside a Flatpak the sandbox glibc is incompatible with host shared libraries,
# so we can't run host Python/Lua under the sandbox runtime — `LD_LIBRARY_PATH`
# tricks hit a `_dl_call_libc_early_init` assertion. The supported way out is
# `flatpak-spawn --host`, which talks to the session-bus Flatpak D-Bus service
# (org.freedesktop.Flatpak.Development) and asks it to spawn a process in the
# host execution environment instead of inside our sandbox. The manifest must
# grant `--talk-name=org.freedesktop.Flatpak` for the D-Bus call to be allowed.
#
# The host process can't see our /app/ contents (sandbox-only), so when we
# spawn host Python/Lua to run `py_func` / `lua_func`, the cwd must be a
# directory both sides can reach. /tmp is shared (--filesystem=/tmp), so we
# stage the testium package there once per process and reuse it for every
# spawn. In source mode (testium under $HOME) the host already sees the
# original path, so we skip the copy.

_staged_testium_path = None


def _get_host_testium_path():
    """Return a path to the testium package that the host can read.

    - Source / wheel / PyInstaller install under $HOME → return testium_path()
      as-is (host sees the same path via --filesystem=home).
    - Flatpak bundle (testium under /app/) → stage a copy under /tmp on first
      call and reuse it for the rest of the process.
    """
    global _staged_testium_path
    if _staged_testium_path is not None:
        return _staged_testium_path

    # Imported lazily to avoid a circular import (paths.py -> api.testium).
    from interpreter.utils.paths import testium_path
    tp = testium_path()

    if not tp.startswith("/app/"):
        _staged_testium_path = tp
        return tp

    staged = tempfile.mkdtemp(prefix="testium_host_", dir="/tmp")
    # copytree refuses to write into an existing dir unless dirs_exist_ok=True.
    # mkdtemp creates the dir, so we copy *into* it.
    for entry in os.listdir(tp):
        src = os.path.join(tp, entry)
        dst = os.path.join(staged, entry)
        if os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst, follow_symlinks=False)
    _staged_testium_path = staged
    atexit.register(shutil.rmtree, staged, ignore_errors=True)
    return staged


_FORWARDED_ENV_KEYS = (
    "HOME", "USER", "LOGNAME", "TMPDIR",
    "XDG_RUNTIME_DIR", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME",
    "DBUS_SESSION_BUS_ADDRESS", "DISPLAY", "WAYLAND_DISPLAY",
    "LANG", "LC_ALL",
)


def flatpak_host_spawn(interp_bin, cmd_args, host_cwd, extra_env=None):
    """Build a flatpak-spawn --host command vector.

    Args:
        interp_bin: absolute path to the host interpreter (e.g. /usr/bin/python3).
        cmd_args: list of arguments passed to the interpreter.
        host_cwd: working directory on the host (must be reachable from host).
        extra_env: optional {name: value} of env vars to set on the host side
                   in addition to the default forwarded set. Values of ""
                   unset the variable on the host.

    Returns a list suitable for subprocess.Popen.
    """
    spawn = ["flatpak-spawn", "--host", f"--directory={host_cwd}"]
    forwarded = {}
    for key in _FORWARDED_ENV_KEYS:
        val = os.environ.get(key)
        if val:
            forwarded[key] = val
    if extra_env:
        forwarded.update(extra_env)
    for k, v in forwarded.items():
        if v == "":
            spawn.append(f"--unset-env={k}")
        else:
            spawn.append(f"--env={k}={v}")
    spawn.append(interp_bin)
    spawn.extend(cmd_args)
    return spawn


def host_console_command(shell_cmd, cwd):
    """Build the argv to start *shell_cmd* as an ordinary interactive console.

    *shell_cmd* is the command the caller chose (a string — shell-split — or
    an argv list); the choice is preserved verbatim.

    Outside Flatpak the command is returned unchanged. Inside Flatpak a bare
    spawn would run in the sandbox under the runtime python3, so a host venv
    (``/path/venv/bin/python3 -m mod``) can't see its pip deps. We simply run
    it on the host with ``flatpak-spawn --host`` so it behaves like any other
    terminal: flatpak-spawn passes the current environment through unchanged
    and the shell (sourced venv, profile, …) sets things up as the user wants.
    No env forwarding or scrubbing — the launcher's leaked PYTHONPATH points at
    /app paths absent on the host, so it's inert there.
    """
    argv = shlex.split(shell_cmd) if isinstance(shell_cmd, str) else list(shell_cmd)
    if not _in_flatpak():
        return argv
    return ["flatpak-spawn", "--host", f"--directory={cwd}", *argv]


def _which_host_flatpak(name):
    """Resolve a binary name (or absolute path) on the host via flatpak-spawn.

    We can't probe /run/host/... because (a) only host-os is mounted there,
    not arbitrary paths like /scratch, and (b) returning a /run/host path
    would be useless — the host-side spawn sees a different filesystem and
    needs the host-native path anyway.
    """
    if os.path.isabs(name):
        cmd = flatpak_host_spawn("/bin/sh", ["-c", f'test -x "{name}"'],
                                 host_cwd="/tmp")
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=10)
        except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
            return ""
        return name if r.returncode == 0 else ""
    cmd = flatpak_host_spawn("/bin/sh", ["-c", f'command -v "{name}"'],
                             host_cwd="/tmp")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return ""
    if r.returncode != 0:
        return ""
    return r.stdout.strip()


def _which(name):
    if tm.OS() == "Windows":
        return sys_app_path_win(name)
    if _in_flatpak():
        return _which_host_flatpak(name)
    if _in_appimage():
        for d in _APPIMAGE_HOST_DIRS:
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return ""
    return sys_app_path_lin(name)


def _probe_env():
    """Subprocess env for probing host binaries.

    In AppImage we still need to scrub APPDIR-prefixed entries; in Flatpak we
    delegate execution to the host via flatpak-spawn so the sandbox env doesn't
    matter, but apply_host_libs is a no-op cost.
    """
    env = os.environ.copy()
    apply_host_libs(env)
    return env


def _run_probe(cmd):
    """Run a probe command, dispatching through flatpak-spawn --host in Flatpak.

    Returns (stdout, stderr) as str, or None on failure.
    """
    if _in_flatpak():
        spawn = flatpak_host_spawn(cmd[0], cmd[1:], host_cwd="/tmp")
        try:
            r = subprocess.run(
                spawn, capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
            return None
        if r.returncode != 0:
            return None
        return r.stdout, r.stderr
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding=tm.sys_encoding(), timeout=10, env=_probe_env(),
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return None
    return r.stdout, r.stderr


def _python_version(path):
    out = _run_probe([path, "-c", "import sys; print(sys.version_info[:3])"])
    if out is None:
        return None
    try:
        return eval(out[0])
    except Exception:
        return None


def _is_python3(path):
    v = _python_version(path)
    return v is not None and v[0] == 3


def _lua_version(path):
    out = _run_probe([path, "-v"])
    if out is None:
        return None
    # On Windows the version banner goes to stderr.
    line = out[0] or out[1]
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
        # In Flatpak we always defer to _which() so even absolute paths are
        # checked from the host's perspective (the sandbox can't see e.g.
        # /scratch/... paths that the user may have configured).
        if os.path.isabs(override) and not _in_flatpak():
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
