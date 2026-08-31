# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Shared logic of the test-item dialogs (spawned child processes):
auto-close decision, argv access, result protocol, last-value store and
frozen-stream mute."""

import json
import os
import platform

AUTO_CLOSE_MS = 2000


def accepts(auto_result):
    """True when the auto_result argument asks to accept the dialog."""
    return auto_result is not None and auto_result.lower() in ("ok", "yes")


def arg_at(args, index):
    """Optional argv slot (dialogs pass trailing options positionally)."""
    return args[index] if len(args) > index else None


def send_result(conn, result, success):
    """Send [result, success] to the parent; print for direct runs."""
    if conn:
        conn.send([result, success])
        conn.close()
    else:
        print(result, end="")


def _store_path(kind, name):
    from interpreter.utils.settings import host_id, SettingsCompany
    if "windows" in platform.system().lower():
        user_path = os.getenv("APPDATA")
    else:
        user_path = os.path.join(os.getenv("HOME"), ".config")
    safe = "".join(c for c in name if c.isalnum() or c in "-_ ").strip()
    fname = ".".join(p for p in (kind, safe, host_id()) if p) + ".json"
    store_dir = os.path.join(user_path, SettingsCompany, "testium_dialogs")
    return store_dir, os.path.join(store_dir, fname)


def load_last(kind, name=""):
    """Previous value stored for this dialog, '' when none. Per host: a
    network home shared by PCs keeps per-machine values."""
    try:
        with open(_store_path(kind, name)[1]) as f:
            return json.load(f)
    except (OSError, ValueError):
        return ""


def save_last(kind, name, value):
    """Store *value*; empty keeps the previous one. Written before the
    caller sends its result: the parent kills the child on receive."""
    if not value:
        return
    store_dir, path = _store_path(kind, name)
    try:
        os.makedirs(store_dir, exist_ok=True)
        with open(path, "w") as f:
            json.dump(value, f)
    except OSError:
        pass


def mute_frozen_streams():
    """cx_freeze flush workaround: no-op every standard stream."""
    import sys
    if not hasattr(sys, "frozen"):
        return

    class _NoStream:
        def write(self, data):
            pass

        def read(self, data):
            pass

        def flush(self):
            pass

        def close(self):
            pass

    for name in ("stdout", "stderr", "stdin",
                 "__stdout__", "__stderr__", "__stdin__"):
        setattr(sys, name, _NoStream())
