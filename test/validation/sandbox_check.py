#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Source-mode check of the script sandbox.

Drives a real TestProcess through the control queue, for Python, Lua and
Tcl: returned value, output routed to the sandbox, state kept between two
scripts, reset, error trace, write to the test variables, stop of a
blocking script, completion, script list, item call, refusal during an
active run, and attachment to a context_id while the run is paused. Run
by run.sh in source mode.
"""
import io
import os
import sys
import threading
import time
from queue import Empty
from multiprocessing import Queue

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

from interpreter.process import TestProcess
from interpreter.utils.test_ctrl import TestSetController
from runtime.tum_except import ETUMRuntimeError

TIMEOUT = 20
LANGS = ("python", "lua", "tcl")

# The child's stdout is echoed here through print(): kept to verify that
# the sandbox output does not reach the log.
_log = io.StringIO()
sys.stdout = _log


def _emit(msg, fd=1):
    os.write(fd, (msg + "\n").encode())


_proc = None


def fail(msg):
    _emit(f"SANDBOX CHECK: FAIL: {msg}", fd=2)
    # The child would keep the output pipe of the caller open.
    if _proc is not None and _proc.is_alive():
        _proc.terminate()
    os._exit(1)


def flatten(tree, out):
    for item_id, node in tree.items():
        out[node["name"]] = item_id
        if node.get("child"):
            flatten(node["child"], out)


class Reader:
    """Status queue reader: sandbox events and run events."""

    def __init__(self, queue):
        self._q = queue
        self.run_finished = False
        self.run_success = None
        self.run_events = []
        self._sandbox = []

    def _poll(self, timeout=0.2):
        try:
            m = self._q.get(timeout=timeout)
        except Empty:
            return
        if m.get("type") == "sandbox":
            self._sandbox.append(m)
        elif "id" in m and m["id"] is None:
            self.run_finished = True
            self.run_success = m.get("success")
        elif m.get("status") in ("started", "paused"):
            self.run_events.append((m["status"], m.get("name")))

    def sandbox_result(self, ctx, timeout=TIMEOUT):
        """Wait for the end of a script: (output, result, error)."""
        output = ""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            while self._sandbox:
                m = self._sandbox.pop(0)
                if m["event"] == "output":
                    output += m["text"]
                elif m["event"] == "finished":
                    return output, m["result"], m["error"]
            self._poll()
        fail(f"{ctx}: no end of script after {timeout} s")

    def wait_run_event(self, wanted, ctx, timeout=TIMEOUT):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if wanted in self.run_events:
                return
            if self.run_finished:
                break
            self._poll()
        fail(f"{ctx}: expected {wanted}, events={self.run_events}")

    def wait_run_finished(self, ctx, timeout=TIMEOUT):
        deadline = time.monotonic() + timeout
        while not self.run_finished and time.monotonic() < deadline:
            self._poll()
        if not self.run_finished:
            fail(f"{ctx}: run did not finish, events={self.run_events}")


CODE = {
    "python": {
        "value": "print('sb_out_python')\n20 + 1",
        "define": "sb_state = 7",
        "read": "sb_state",
        "error": "def sb_fail():\n    raise ValueError('sb_boom')\nsb_fail()",
        "error_needles": ("ValueError: sb_boom", "line 2, in sb_fail"),
        "setgd": "tm.setgd('sb_gd_python', [1, 'a'])",
        "block": "import time\ntime.sleep(120)",
        "complete": ("sb_st", "sb_state"),
        "ctx_read": "import ctx_state\nctx_state.value",
        "ctx_write": "ctx_state.value = 6",
    },
    "lua": {
        "value": "print('sb_out_lua')\nreturn 20 + 1",
        "define": "sb_state = 7",
        "read": "sb_state",
        "error": "function sb_fail()\n    error('sb_boom')\nend\nsb_fail()",
        "error_needles": ("sb_boom", "sandbox:2"),
        "setgd": "local tm = require('tm')\ntm.setgd('sb_gd_lua', {1, 'a'})",
        "block": "while true do end",
        "complete": ("sb_st", "sb_state"),
        "ctx_read": "ctx_value",
        "ctx_write": "ctx_value = 6",
    },
    "tcl": {
        "value": "puts sb_out_tcl\nexpr {20 + 1}",
        "define": "set sb_state 7",
        "read": "set sb_state",
        "error": "proc sb_fail {} {\n    error sb_boom\n}\nsb_fail",
        "error_needles": ("sb_boom", '(procedure "sb_fail" line 2)',
                          "(sandbox line 4)"),
        "setgd": "tm::setgd sb_gd_tcl [tm::list {1 a}]",
        "block": "after 120000",
        "complete": ("$sb_st", "$sb_state"),
        "ctx_read": "set ::ctx_value",
        "ctx_write": "set ::ctx_value 6",
    },
}


def main():
    test_file = os.path.join(HERE, "sandbox", "test.tum")
    msg_queue = Queue()
    ctrl = TestSetController()
    global _proc
    proc = _proc = TestProcess(test_file, msg_queue, ctrl, [], {})
    proc.start()

    loaded = threading.Event()
    threading.Thread(
        target=lambda: (ctrl.control("loaded"), loaded.set()), daemon=True
    ).start()
    while not loaded.wait(timeout=0.1):
        if not proc.is_alive():
            fail("TestProcess died during load")

    ids = {}
    flatten(ctrl.control("tree"), ids)
    reader = Reader(msg_queue)

    def run(lang, code, session=None, ctx=""):
        ctrl.control("sandbox_run", lang=lang, code=code, session=session)
        return reader.sandbox_result(f"{lang} {ctx}")

    # --- Test loaded, no run: process owned by the sandbox.
    for lang in LANGS:
        c = CODE[lang]

        out, res, err = run(lang, c["value"], ctx="value")
        if err is not None or res != 21:
            fail(f"{lang}: value script gave result={res!r} error={err!r}")
        if f"sb_out_{lang}" not in out:
            fail(f"{lang}: printed text not received, output={out!r}")

        run(lang, c["define"], ctx="define")
        out, res, err = run(lang, c["read"], ctx="read")
        if res != 7:
            fail(f"{lang}: state not kept between scripts: {res!r} {err!r}")

        names = ctrl.control("sandbox_complete", lang=lang,
                             prefix=c["complete"][0], session=None)
        if c["complete"][1] not in names:
            fail(f"{lang}: completion of {c['complete'][0]!r} gave {names}")

        ctrl.control("sandbox_reset", lang=lang, session=None)
        out, res, err = run(lang, c["read"], ctx="read after reset")
        if res == 7:
            fail(f"{lang}: state still there after reset")

        out, res, err = run(lang, c["error"], ctx="error")
        if err is None:
            fail(f"{lang}: failing script reported no error")
        for needle in c["error_needles"]:
            if needle not in err:
                fail(f"{lang}: {needle!r} not in the error:\n{err}")

        run(lang, c["setgd"], ctx="setgd")
        value = ctrl.control("get_gd_vars").get(f"sb_gd_{lang}")
        if value != [1, "a"]:
            fail(f"{lang}: setgd not seen in the test variables: {value!r}")

        ctrl.control("sandbox_run", lang=lang, code=c["block"], session=None)
        time.sleep(0.5)
        try:
            ctrl.control("sandbox_run", lang=lang, code=c["read"],
                         session=None)
        except ETUMRuntimeError as e:
            if "already running" not in str(e):
                fail(f"{lang}: unexpected refusal message: {e}")
        else:
            fail(f"{lang}: second script accepted while one is running")
        if ctrl.control("sandbox_stop") is not True:
            fail(f"{lang}: sandbox_stop found no running script")
        out, res, err = reader.sandbox_result(f"{lang} stop")
        if err is None:
            fail(f"{lang}: stopped script reported no error")
        out, res, err = run(lang, c["value"], ctx="after stop")
        if res != 21:
            fail(f"{lang}: session not usable after stop: {res!r} {err!r}")

    scripts = ctrl.control("sandbox_scripts")
    for lang, name in (("python", "ctx.py"), ("lua", "ctx.lua"),
                       ("tcl", "ctx.tcl")):
        expected = os.path.join(HERE, "sandbox", name)
        if scripts.get(lang) != [expected]:
            fail(f"sandbox_scripts[{lang}] = {scripts.get(lang)}, "
                 f"expected [{expected}]")

    for lang, item in (("python", "py set"), ("lua", "lua set"),
                       ("tcl", "tcl set")):
        call = ctrl.control("sandbox_item_call", item_id=ids[item])
        if call["lang"] != lang or call["session"] is not None \
                or call["unresolved"]:
            fail(f"item call of '{item}': {call}")
        out, res, err = run(lang, call["code"], ctx="item call")
        if res != 5:
            fail(f"item call of '{item}' gave {res!r} {err!r}:\n"
                 f"{call['code']}")
    call = ctrl.control("sandbox_item_call", item_id=ids["unresolved"])
    if call["unresolved"] != ["sandbox_undefined_dir",
                              "sandbox_undefined_value"]:
        fail(f"unresolved variables of an item call: {call['unresolved']}")
    try:
        ctrl.control("sandbox_item_call", item_id=ids["slow"])
    except ETUMRuntimeError:
        pass
    else:
        fail("sandbox_item_call accepted a sleep item")

    # --- Active run: refused. Paused run: attached to the contexts.
    ctrl.control("add_breakpoint", item_id=ids["first stop"])
    ctrl.control("add_breakpoint", item_id=ids["second stop"])
    ctrl.control("execute")
    reader.wait_run_event(("started", "slow"), "run")
    try:
        ctrl.control("sandbox_run", lang="tcl", code="expr 1", session=None)
    except ETUMRuntimeError as e:
        if "stopped or paused" not in str(e):
            fail(f"unexpected refusal message during a run: {e}")
    else:
        fail("script accepted during an active run")
    if ctrl.control("sandbox_sessions", lang="tcl") != []:
        fail("sessions listed during an active run")

    reader.wait_run_event(("paused", "first stop"), "run")
    for lang, session in (("python", "pyctx"), ("lua", "luactx"),
                          ("tcl", "tclctx")):
        c = CODE[lang]
        sessions = ctrl.control("sandbox_sessions", lang=lang)
        if sessions != [session]:
            fail(f"{lang}: sessions at pause = {sessions}")
        out, res, err = run(lang, c["ctx_read"], session, "context read")
        if res != 5:
            fail(f"{lang}: context state read {res!r} {err!r}, expected 5")
        out, res, err = run(lang, c["ctx_write"], session, "context write")
        if err is not None:
            fail(f"{lang}: context write failed: {err}")
    try:
        ctrl.control("sandbox_run", lang="tcl", code="expr 1",
                     session="no_such_context")
    except ETUMRuntimeError as e:
        if "not active" not in str(e):
            fail(f"unexpected message for an unknown context: {e}")
    else:
        fail("unknown context accepted")

    # The 'get' items expect the value written from the sandbox.
    ctrl.control("cont")
    reader.wait_run_event(("paused", "second stop"), "run")
    ctrl.control("sandbox_reset", lang="lua", session="luactx")
    ctrl.control("sandbox_reset", lang="tcl", session="tclctx")
    # The 'fresh' items expect a new process.
    ctrl.control("cont")
    reader.wait_run_finished("run")
    if reader.run_success is not True:
        fail("the run failed: a context did not see the sandbox write, "
             "or was not restarted by the reset")

    if proc.is_alive():
        ctrl.control("close")
    proc.join(10)
    if proc.is_alive():
        proc.terminate()

    log = _log.getvalue()
    for lang in LANGS:
        if f"sb_out_{lang}" in log:
            fail(f"{lang}: sandbox output found in the test log")

    _emit("SANDBOX CHECK: PASS")
    os._exit(0)


if __name__ == "__main__":
    main()
