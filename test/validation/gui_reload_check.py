#!/usr/bin/env python3
"""Source-mode check: repeated GUI reloads must not leak resources.

Drives a headless MainWindow, reloads a small .tum N times and asserts open
fds, live threads and sys.path length stay flat — guards the reload cleanup
(control queues, stdout-capture pipe/thread, sys.path). Skips cleanly if the
GUI stack is unavailable. Run by run.sh in source mode.
"""
import gc
import os
import sys
import threading
import multiprocessing

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
# `import testium` (src) and `import main_win` (src/testium).
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

N = 15


def _emit(msg, fd=1):
    # MainWindow redirects sys.stdout into its GUI log; write to the real fd.
    os.write(fd, (msg + "\n").encode())


def skip(msg):
    _emit(f"GUI RELOAD CHECK: SKIP — {msg}")
    sys.exit(0)


def fail(msg):
    _emit(f"GUI RELOAD CHECK: FAIL — {msg}", fd=2)
    sys.exit(1)


def _fds():
    # Linux-only; elsewhere fds aren't compared.
    try:
        return len(os.listdir("/proc/self/fd"))
    except OSError:
        return -1


def main():
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QCoreApplication
        from main_win.testium_win import MainWindow
    except Exception as e:
        skip(f"GUI stack unavailable ({e})")

    test_file = os.path.join(HERE, "gui_reload", "test.tum")
    app = QApplication([])
    win = MainWindow(test_file=test_file, config_files=[])
    QCoreApplication.processEvents()
    if win.testFile is None:
        fail("sample test did not load")

    def measure():
        QCoreApplication.processEvents()
        return (_fds(), threading.active_count(), len(sys.path))

    win.file_manager.reload(test_file)  # warm-up
    gc.collect()
    base = measure()
    for _ in range(N):
        win.file_manager.reload(test_file)
    gc.collect()
    end = measure()

    win.file_manager.clear_process()  # reap the child before exiting
    d_fd, d_thr, d_sp = (e - b for e, b in zip(end, base))
    fd_ok = _fds() < 0 or d_fd <= 4  # skip fd check off Linux
    if not fd_ok or d_thr > 4 or d_sp > 1:
        fail(f"leak over {N} reloads: fds {d_fd:+d} threads {d_thr:+d} sys.path {d_sp:+d}")
    _emit(f"GUI RELOAD CHECK: PASS ({N} reloads, "
          f"fds {d_fd:+d} threads {d_thr:+d} sys.path {d_sp:+d})")
    app.quit()
    os._exit(0)


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    main()
