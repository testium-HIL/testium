#!/usr/bin/env python3
"""Source-mode check: fold/check/breakpoint states survive a reload.

States are keyed by item path, so a reload of the same file must keep them
even when items were added (item count changed). States and the log-file
choice are stored per test file: another file must not inherit them and
each file must restore its own on return and after a restart. The stored
entries are capped (LRU). Runs a headless MainWindow against a throwaway
HOME. Run by run.sh in source mode.
"""
import os
import platform
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

# Throwaway config/settings dir, set before any testium import. TestiumSettings
# roots itself at $APPDATA on Windows and $HOME/.config elsewhere, so redirect
# both. .config must pre-exist: only the two last levels are created.
WORK = tempfile.mkdtemp(prefix="testium-state-check-")
os.environ["HOME"] = WORK
os.makedirs(os.path.join(WORK, ".config"))
if "windows" in platform.system().lower():
    os.environ["APPDATA"] = WORK
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FIXTURE = """main:
    name: State check
    steps:
        - group:
            name: G
            steps:
{extra}                - sleep:
                    name: s1
                    timeout: 0.01
                - sleep:
                    name: s2
                    timeout: 0.01
        - sleep:
            name: Brief
            timeout: 0.01
"""

EXTRA_STEP = """                - sleep:
                    name: s0
                    timeout: 0.01
"""

OTHER = """main:
    name: Other file
    steps:
        - sleep:
            name: alone
            timeout: 0.01
"""


def _emit(msg, fd=1):
    os.write(fd, (msg + "\n").encode())


def skip(msg):
    _emit(f"GUI STATE CHECK: SKIP — {msg}")
    os._exit(0)


def fail(msg):
    _emit(f"GUI STATE CHECK: FAIL — {msg}", fd=2)
    os._exit(1)


def main():
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QCoreApplication, Qt
        import interpreter.utils.settings as prefs
        from main_win.testium_win import MainWindow
    except Exception as e:
        skip(f"GUI stack unavailable ({e})")

    test_file = os.path.join(WORK, "test.tum")
    other_file = os.path.join(WORK, "other.tum")
    with open(test_file, "w") as f:
        f.write(FIXTURE.format(extra=""))
    with open(other_file, "w") as f:
        f.write(OTHER)

    # Persist to the throwaway config: later prefs.init() calls re-read it.
    prefs.init()
    prefs.settings.set_value(prefs.settings.SettingsShowCheckboxes, True)
    prefs.settings.sync()

    app = QApplication([])
    win = MainWindow(test_file=test_file, config_files=[])
    QCoreApplication.processEvents()
    if win.testFile is None:
        fail("fixture did not load")

    def by_name(name):
        for it in win.treeTests._all_items():
            if it.name == name:
                return it
        fail(f"item '{name}' not found")

    def states():
        d = {}
        for it in win.treeTests._all_items():
            d[it.name] = (not it.isExpanded(),
                          it.checkState(0) == Qt.Checked,
                          it.isBreakpoint())
        return d

    def assert_marks(ctx):
        s = states()
        if not s["Brief"][2]:
            fail(f"{ctx}: breakpoint on 'Brief' lost ({s})")
        if s["s2"][1]:
            fail(f"{ctx}: 's2' should be unchecked ({s})")
        if not s["G"][0]:
            fail(f"{ctx}: group 'G' should be folded ({s})")
        n_bp = sum(1 for v in s.values() if v[2])
        if n_bp != 1:
            fail(f"{ctx}: expected exactly 1 breakpoint, got {n_bp}")

    def set_marks():
        item = by_name("Brief")
        item.setBreakpointState(True)
        win.test_service.add_breakpoint(item.id)
        by_name("s2").setCheckState(0, Qt.Unchecked)
        QCoreApplication.processEvents()
        by_name("G").setExpanded(False)

    # 1. Set the three marks, reload the same file: all kept.
    set_marks()
    count0 = win.treeTests.getItemCount()
    win.file_manager.reload(test_file)
    assert_marks("reload same file")

    # 2. Add an item BEFORE the marked ones: count changes, positional
    # matching would shift — path keys must not.
    with open(test_file, "w") as f:
        f.write(FIXTURE.format(extra=EXTRA_STEP))
    win.file_manager.reload(test_file)
    if win.treeTests.getItemCount() == count0:
        fail("item count did not change after fixture edit")
    assert_marks("reload with added item")

    # 3. Different file: the first file's marks must not leak into it.
    win.editLogFilePath.setText("log_a.log")
    win.file_manager.reload(other_file)
    if any(v[2] for v in states().values()):
        fail(f"breakpoint leaked to another file ({states()})")
    if not all(v[1] for v in states().values()):
        fail(f"unchecked state leaked to another file ({states()})")
    win.editLogFilePath.setText("log_b.log")

    # 4. Back to the first file: marks and log choice restored; the other
    # file keeps its own log choice too.
    win.file_manager.reload(test_file)
    assert_marks("switch back")
    if win.editLogFilePath.text() != "log_a.log":
        fail(f"log choice not restored ({win.editLogFilePath.text()!r})")
    win.file_manager.reload(other_file)
    if win.editLogFilePath.text() != "log_b.log":
        fail(f"other file log choice lost ({win.editLogFilePath.text()!r})")

    # 5. Restart persistence: close on the fixture (saves settings), reopen:
    # all restored.
    win.file_manager.reload(test_file)
    win.close()
    QCoreApplication.processEvents()

    win = MainWindow(test_file=test_file, config_files=[])
    QCoreApplication.processEvents()
    if win.testFile is None:
        fail("fixture did not load on restart")
    assert_marks("restart")
    if win.editLogFilePath.text() != "log_a.log":
        fail(f"log choice not restored on restart "
             f"({win.editLogFilePath.text()!r})")

    # 6. LRU cap: flood with fake entries, trim must keep the newest.
    key_kept = win._file_state_key(test_file)
    win.stash_file_state(test_file)
    for i in range(win.FileStatesMax + 5):
        prefs.settings.set_value(
            prefs.SettingsItem(f"itemstates.fake{i:03d}", list, []),
            [f"/fake/{i}.tum", float(i), [], "", False])
    win._trim_file_states()
    names = prefs.settings.option_names("itemstates.")
    if len(names) != win.FileStatesMax:
        fail(f"LRU cap not enforced ({len(names)} entries)")
    if key_kept not in names:
        fail("LRU trim dropped the most recent entry")

    win.file_manager.clear_process()
    _emit("GUI STATE CHECK: PASS")
    os._exit(0)


if __name__ == "__main__":
    main()
