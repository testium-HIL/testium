#!/usr/bin/env python3
"""Source-mode check: settings survive two concurrent instances.

sync() merges only the keys written by this process, so two instances
writing disjoint keys must both keep them on disk, whatever the sync
order. remove_value must survive the merge. A corrupt file must not
crash startup nor be wiped at init. Two processes racing the first-run
creation must both succeed. Run by run.sh in source mode.
"""
import os
import platform
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

# Throwaway config/settings dir, set before any testium import.
WORK = tempfile.mkdtemp(prefix="testium-settings-check-")
os.environ["HOME"] = WORK
os.makedirs(os.path.join(WORK, ".config"))
if "windows" in platform.system().lower():
    os.environ["APPDATA"] = WORK

from interpreter.utils.settings import TestiumSettings, SettingsItem  # noqa: E402


def fail(msg):
    print(f"SETTINGS CHECK: FAIL — {msg}", file=sys.stderr)
    sys.exit(1)


def item(name):
    return SettingsItem(name, str, "")


def main():
    base = TestiumSettings()
    base.set_value(item("keep"), "kept")
    base.sync()
    fname = base.settings_fname

    # 1. Two instances, disjoint keys, both sync orders.
    a, b = TestiumSettings(), TestiumSettings()
    a.set_value(item("keyA"), "va")
    b.set_value(item("keyB"), "vb")
    a.sync()
    b.sync()
    c, d = TestiumSettings(), TestiumSettings()
    c.set_value(item("keyC"), "vc")
    d.set_value(item("keyD"), "vd")
    d.sync()
    c.sync()
    check = TestiumSettings()
    for name, expected in [("keep", "kept"), ("keyA", "va"), ("keyB", "vb"),
                           ("keyC", "vc"), ("keyD", "vd")]:
        got = check.value(item(name))
        if got != expected:
            fail(f"'{name}' = {got!r} after merge, expected {expected!r}")

    # 2. remove_value survives another instance's later sync.
    e, f = TestiumSettings(), TestiumSettings()
    e.remove_value("keya")
    e.sync()
    f.set_value(item("keyE"), "ve")
    f.sync()
    check = TestiumSettings()
    if check.value(item("keyA")) != "":
        fail("removed 'keyA' came back after merge")
    if check.value(item("keyE")) != "ve":
        fail("'keyE' lost after merge with a removal")

    # 3. Corrupt file: startup on defaults, file untouched until a sync.
    with open(fname, "w") as fd:
        fd.write("garbage without a section header\n")
    g = TestiumSettings()
    if g.value(item("keep"), "default") != "default":
        fail("corrupt file did not fall back to defaults")
    with open(fname) as fd:
        if "garbage" not in fd.read():
            fail("corrupt file was rewritten at init")
    g.set_value(item("fresh"), "vf")
    g.sync()
    check = TestiumSettings()
    if check.value(item("fresh")) != "vf":
        fail("could not write over a corrupt file")

    # 4. First-run creation race: two processes on a fresh config dir.
    work2 = tempfile.mkdtemp(prefix="testium-settings-race-")
    os.makedirs(os.path.join(work2, ".config"))
    env = dict(os.environ, HOME=work2, APPDATA=work2)
    script = ("import interpreter.utils.settings as s; "
              "s.TestiumSettings()")
    procs = [subprocess.Popen([sys.executable, "-c", script],
                              env=env, cwd=os.path.join(SRC, "testium"),
                              stderr=subprocess.PIPE)
             for _ in range(2)]
    for p in procs:
        _, err = p.communicate(timeout=30)
        if p.returncode != 0:
            fail(f"first-run race crashed: {err.decode(errors='replace')}")

    print("SETTINGS CHECK: PASS")


if __name__ == "__main__":
    main()
