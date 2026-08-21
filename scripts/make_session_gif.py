# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Regenerate doc/testium_session.gif.

Runs the GUI offscreen on scripts/session_gif/demo.tum and plays a
scripted scenario: set a breakpoint, start, pause on it, select a played
step (the log follows), open the Variables panel, add a variable,
resume. One frame is captured every 150 ms, then assembled into the GIF.

Usage (needs testium's dependencies and Pillow):
    test/tmp/.venv/bin/python3 scripts/make_session_gif.py
"""

import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO, "scripts", "session_gif")
OUTPUT = os.path.join(REPO, "doc", "testium_session.gif")

TICK_MS = 150
WINDOW = (1280, 800)
LOG_DOCK_WIDTH = 500
CURSOR_REST = (620, 470)
MAX_FRAMES = 400


def ease(t):
    return t * t * (3 - 2 * t)


class Scenario:
    """Frame-by-frame step player: cursor moves, clicks, typing, waits."""

    def __init__(self, start_pos):
        self.pos = start_pos
        self.steps = []
        self.effect = None
        self._move = None
        self._wait_frames = 0

    def move(self, target, frames=8):
        self.steps.append(("move", target, frames))

    def click(self, action=None):
        self.steps.append(("click", action))

    def type_text(self, edit, text):
        for i in range(1, len(text) + 1):
            self.steps.append(("type", edit, text[:i]))

    def hold(self, frames):
        self.steps.append(("hold", frames))

    def wait_until(self, predicate):
        self.steps.append(("wait", predicate))

    def run(self, action):
        self.steps.append(("run", action))

    def advance(self):
        """One frame; returns False when the scenario is over."""
        self.effect = None
        while True:
            if self._move is not None:
                target, total, n = self._move
                n += 1
                t = ease(n / total)
                x0, y0 = self._move_from
                tx, ty = target() if callable(target) else target
                self.pos = (round(x0 + (tx - x0) * t),
                            round(y0 + (ty - y0) * t))
                self._move = None if n >= total else (target, total, n)
                return True
            if self._wait_frames > 0:
                self._wait_frames -= 1
                return True
            if not self.steps:
                return False
            step = self.steps.pop(0)
            kind = step[0]
            if kind == "move":
                self._move_from = self.pos
                self._move = (step[1], step[2], 0)
            elif kind == "click":
                self.effect = "click"
                if step[1] is not None:
                    step[1]()
                return True
            elif kind == "type":
                step[1].setText(step[2])
                return True
            elif kind == "hold":
                self._wait_frames = step[1]
            elif kind == "wait":
                if not step[1]():
                    self.steps.insert(0, step)
                    return True
            elif kind == "run":
                step[1]()


def capture(frames_dir):
    """Child process: drive the GUI offscreen and save one PNG per tick."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["HOME"] = os.path.join(frames_dir, "home")
    os.makedirs(os.path.join(os.environ["HOME"], ".config"))
    sys.path.insert(0, os.path.join(REPO, "src", "testium"))
    sys.path.insert(0, os.path.join(REPO, "src"))

    from PySide6.QtCore import QPoint, Qt, QTimer
    from PySide6.QtWidgets import QApplication

    from gui.run_presenter import TestState
    from main_win.testium_win import MainWindow
    import interpreter.utils.settings as prefs

    app = QApplication([])
    prefs.init()
    win = MainWindow(test_file=os.path.join(FIXTURES, "demo.tum"),
                     config_files=[])
    win.resize(*WINDOW)
    win.DocDockWidget.hide()
    win.itemDock.hide()
    win.variablesDock.hide()
    win.show()
    win.resizeDocks([win.logDockWidget], [LOG_DOCK_WIDTH], Qt.Horizontal)

    items = {it.name: it for it in win.treeTests._all_items()}
    bp_item = items["Acquire three samples"]
    sel_item = items["Read the sensor temperature"]

    def widget_center(widget):
        c = widget.mapTo(win, QPoint(widget.width() // 2,
                                     widget.height() // 2))
        return (c.x(), c.y())

    def action_center(action):
        for bar in (win.stepBar, win.toolBar):
            w = bar.widgetForAction(action)
            if w is not None:
                return widget_center(w)
        return CURSOR_REST

    def row_point(item, gutter=False):
        rect = win.treeTests.visualItemRect(item)
        p = win.treeTests.viewport().mapTo(
            win, QPoint(12 if gutter else 120, rect.center().y()))
        return (p.x(), p.y())

    def set_breakpoint():
        bp_item.setBreakpointState(True)
        win.test_service.add_breakpoint(bp_item.id)

    def show_variables():
        # Below the tree, not stacked under the log column.
        win.addDockWidget(Qt.BottomDockWidgetArea, win.variablesDock)
        win.variablesDock.show()
        win.variablesDock.raise_()
        win.resizeDocks([win.variablesDock], [240], Qt.Vertical)

    sc = Scenario(CURSOR_REST)
    # Breakpoint on the acquisition loop.
    sc.move(lambda: row_point(bp_item, gutter=True), 8)
    sc.click(set_breakpoint)
    sc.hold(4)
    # Start; the run pauses on the breakpoint.
    sc.move(lambda: action_center(win.actionStart_test), 8)
    sc.click(win.on_actionStart_test_triggered)
    sc.wait_until(lambda: win.runner.state == TestState.PAUSED)
    sc.hold(5)
    # Select a played step: the log repositions on it.
    sc.move(lambda: row_point(sel_item), 8)
    sc.click(lambda: win.treeTests.setCurrentItem(sel_item))
    sc.hold(6)
    # Open the Variables panel and add a variable.
    sc.move(lambda: action_center(win.actionVariables), 8)
    sc.click(show_variables)
    sc.hold(4)
    sc.move(lambda: widget_center(win.variablesDock.newKeyEdit), 8)
    sc.click()
    sc.type_text(win.variablesDock.newKeyEdit, "operator")
    sc.move(lambda: widget_center(win.variablesDock.newValueEdit), 5)
    sc.click()
    sc.type_text(win.variablesDock.newValueEdit, "'bench-2'")
    sc.move(lambda: widget_center(win.variablesDock.addVarButton), 5)
    sc.click(win.variablesDock.addVarButton.click)
    sc.hold(8)
    # Resume and let the run finish.
    sc.move(lambda: action_center(win.actionStart_test), 8)
    sc.click(win.on_actionStart_test_triggered)
    sc.wait_until(lambda: win.runner.state == TestState.IDLE)
    sc.hold(10)

    state = {"n": 0}
    cursors = []

    def tick():
        try:
            n = state["n"]
            alive = sc.advance()
            win.grab().save(os.path.join(frames_dir, f"frame{n:03d}.png"))
            cursors.append({"x": sc.pos[0], "y": sc.pos[1],
                            "effect": sc.effect})
            state["n"] += 1
            if not alive:
                with open(os.path.join(frames_dir, "cursors.json"), "w") as f:
                    json.dump(cursors, f)
                os._exit(0)
            if n > MAX_FRAMES:
                os.write(2, b"capture did not finish\n")
                os._exit(1)
        except Exception as e:
            os.write(2, f"capture error: {e!r}\n".encode())
            os._exit(2)

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(TICK_MS)
    app.exec()


def draw_cursor(img, x, y, effect):
    from PIL import ImageDraw
    d = ImageDraw.Draw(img, "RGBA")
    if effect == "click":
        d.ellipse([x - 13, y - 13, x + 13, y + 13],
                  outline=(30, 110, 220, 200), width=3)
    pts = [(x, y), (x, y + 17), (x + 4, y + 13), (x + 7, y + 20),
           (x + 10, y + 18), (x + 7, y + 12), (x + 12, y + 12)]
    d.polygon(pts, fill=(20, 20, 20, 255), outline=(255, 255, 255, 255))


def assemble(frames_dir):
    import glob
    from PIL import Image

    paths = sorted(glob.glob(os.path.join(frames_dir, "frame*.png")))
    with open(os.path.join(frames_dir, "cursors.json")) as f:
        cursors = json.load(f)
    frames = []
    for path, c in zip(paths, cursors):
        img = Image.open(path).convert("RGB")
        draw_cursor(img, c["x"], c["y"], c["effect"])
        frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))
    durations = [900] + [TICK_MS] * (len(frames) - 2) + [3000]
    frames[0].save(OUTPUT, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True)
    print(f"{OUTPUT}: {len(frames)} frames, "
          f"{os.path.getsize(OUTPUT) // 1024} KiB")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--capture":
        capture(sys.argv[2])
        return
    with tempfile.TemporaryDirectory(prefix="testium-gif-") as frames_dir:
        subprocess.run([sys.executable, os.path.abspath(__file__),
                        "--capture", frames_dir], check=True, timeout=180)
        assemble(frames_dir)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.set_start_method("spawn")
    main()
