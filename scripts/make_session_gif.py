# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Regenerate doc/testium_session.gif.

Runs the GUI offscreen on scripts/session_gif/demo.tum, captures a frame
every 150 ms while a scripted mouse clicks Start and the run completes,
then assembles the frames into the GIF.

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
WINDOW = (1280, 675)
LOG_DOCK_WIDTH = 500
CURSOR_REST = (620, 470)     # over the test tree
CURSOR_PARK = (500, 360)
MOVE0, MOVE1 = 4, 14         # frames of travel to the Start button
CLICK0, CLICK1 = 15, 17      # frames with the button pressed


def ease(t):
    return t * t * (3 - 2 * t)


def capture(frames_dir):
    """Child process: drive the GUI offscreen and save one PNG per tick."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["HOME"] = os.path.join(frames_dir, "home")
    os.makedirs(os.path.join(os.environ["HOME"], ".config"))
    sys.path.insert(0, os.path.join(REPO, "src", "testium"))
    sys.path.insert(0, os.path.join(REPO, "src"))

    from PySide6.QtCore import QPoint, Qt, QTimer
    from PySide6.QtWidgets import QApplication

    from main_win.test_runner import TestState
    from main_win.testium_win import MainWindow
    import interpreter.utils.settings as prefs

    app = QApplication([])
    prefs.init()
    win = MainWindow(test_file=os.path.join(FIXTURES, "demo.tum"),
                     config_files=[])
    win.resize(*WINDOW)
    win.DocDockWidget.hide()
    win.show()
    win.resizeDocks([win.logDockWidget], [LOG_DOCK_WIDTH], Qt.Horizontal)

    btn = win.stepBar.widgetForAction(win.actionStart_test)
    center = btn.mapTo(win, QPoint(btn.width() // 2, btn.height() // 2))
    target = (center.x(), center.y())
    park1 = CLICK1 + 11      # end of the travel back to the tree

    state = {"n": 0, "idle_since": None}
    cursors = []

    def cursor_pos(n):
        if n < MOVE0:
            return CURSOR_REST, None
        if n <= MOVE1:
            t = ease((n - MOVE0) / (MOVE1 - MOVE0))
            return (round(CURSOR_REST[0] + (target[0] - CURSOR_REST[0]) * t),
                    round(CURSOR_REST[1] + (target[1] - CURSOR_REST[1]) * t)), None
        if n <= CLICK1:
            return target, "click"
        if n <= park1:
            t = ease((n - CLICK1) / (park1 - CLICK1))
            return (round(target[0] + (CURSOR_PARK[0] - target[0]) * t),
                    round(target[1] + (CURSOR_PARK[1] - target[1]) * t)), None
        return CURSOR_PARK, None

    def tick():
        try:
            n = state["n"]
            if n == CLICK0:
                btn.setDown(True)
            if n == CLICK1:
                btn.setDown(False)
                win.on_actionStart_test_triggered()
            win.grab().save(os.path.join(frames_dir, f"frame{n:03d}.png"))
            pos, effect = cursor_pos(n)
            cursors.append({"x": pos[0], "y": pos[1], "effect": effect})
            state["n"] += 1
            if n > CLICK1 + 5 and win.runner.state == TestState.IDLE:
                if state["idle_since"] is None:
                    state["idle_since"] = n
                elif n - state["idle_since"] >= 10:
                    with open(os.path.join(frames_dir, "cursors.json"), "w") as f:
                        json.dump(cursors, f)
                    os._exit(0)
            if n > 300:
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
                        "--capture", frames_dir], check=True, timeout=120)
        assemble(frames_dir)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.set_start_method("spawn")
    main()
