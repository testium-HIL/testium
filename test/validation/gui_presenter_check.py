#!/usr/bin/env python3
"""Source-mode check of the run presenter, without any toolkit.

Drives gui/run_presenter.py with fake view/scheduler/service: state
machine, run log opening and rotation, pause icon flip, exit code and
the run-and-close path. No PySide6 import anywhere in the chain. Run by
run.sh in source mode.
"""
import os
import queue
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, os.path.join(SRC, "testium"))
sys.path.insert(0, SRC)

WORK = tempfile.mkdtemp(prefix="testium-presenter-")
os.environ["HOME"] = WORK
os.makedirs(os.path.join(WORK, ".config"))
import platform
if "windows" in platform.system().lower():
    os.environ["APPDATA"] = WORK

import interpreter.utils.settings as prefs
prefs.init()

from gui.run_presenter import RunPresenter, TestState


def fail(msg):
    print(f"GUI PRESENTER CHECK: FAIL — {msg}", file=sys.stderr)
    sys.exit(1)


class FakeView:
    def __init__(self, log_path):
        self._log_path = log_path
        self.ui_states = []
        self.log_lines = []
        self.lights = []
        self.start_actions = []
        self.elapsed = []
        self.messages = []
        self.log_file_name = None
        self.sink = None
        self.closed = False
        self.succeeded = True
        self.confirm_abort = False
        self.confirm_calls = 0

    def apply_run_ui(self, state):
        self.ui_states.append(state)

    def set_start_action(self, text, icon):
        self.start_actions.append((text, icon))

    def set_status_light(self, color):
        self.lights.append(color)

    def set_elapsed(self, text):
        self.elapsed.append(text)

    def append_log(self, text):
        self.log_lines.append(text)

    def clear_log(self):
        self.log_lines.clear()

    def show_transient_message(self, text):
        self.messages.append(text)

    def confirm_abort_cleanup(self):
        self.confirm_calls += 1
        return self.confirm_abort

    def can_start(self):
        return True

    def test_file(self):
        return "/tmp/fake.tum"

    def log_config(self):
        return (self._log_path, bool(self._log_path))

    def set_log_file_name(self, path):
        self.log_file_name = path

    def report_config(self):
        return ("", "", [])

    def attach_log_sink(self, handle):
        self.sink = handle

    def detach_log_sink(self):
        self.sink = None

    def read_captured(self):
        return ""

    def reset_run_marks(self):
        pass

    def clear_current_marks(self):
        pass

    def run_succeeded(self):
        return self.succeeded

    def close_window(self):
        self.closed = True


class FakeScheduler:
    def __init__(self):
        self.timers = {}

    def every(self, name, interval_ms, tick):
        self.timers[name] = tick

    def once(self, name, delay_ms, fire):
        self.timers[name] = fire

    def cancel(self, name):
        self.timers.pop(name, None)

    def tick(self, name):
        self.timers[name]()


class FakeService:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*a, **k):
            self.calls.append((name,) + a)
            return a[0] if a else None
        return call


class FakeSandboxView:
    def __init__(self):
        self.text = ""
        self.lang = None
        self.sessions = None
        self.state = None
        self.file = None
        self.output = []
        self.confirm_answer = True
        self.confirm_calls = 0
        self.open_path = None
        self.save_path = None
        self.completions = None

    def code(self):
        return self.text

    def set_code(self, text):
        self.text = text

    def set_language(self, lang):
        self.lang = lang

    def set_sessions(self, names, current):
        self.sessions = (names, current)

    def set_sandbox_state(self, enabled, running):
        self.state = (enabled, running)

    def set_file_label(self, name, path):
        self.file = (name, path)

    def append_output(self, text, kind):
        self.output.append((kind, text))

    def confirm(self, question):
        self.confirm_calls += 1
        return self.confirm_answer

    def ask_open_path(self, start_dir):
        return self.open_path

    def ask_save_path(self, start, extension):
        return self.save_path

    def show_completions(self, prefix, names):
        self.completions = (prefix, names)


class FakeSandboxService:
    def __init__(self):
        self.calls = []
        self.contexts = {"tcl": ["bench"]}
        self.scripts = {}
        self.refuse = None
        self.unresolved = []

    def sandbox_run(self, lang, code, session=None):
        if self.refuse:
            from runtime.tum_except import ETUMRuntimeError
            raise ETUMRuntimeError(self.refuse)
        self.calls.append(("run", lang, code, session))

    def sandbox_stop(self):
        self.calls.append(("stop",))
        return True

    def sandbox_reset(self, lang, session=None):
        self.calls.append(("reset", lang, session))

    def sandbox_sessions(self, lang):
        return list(self.contexts.get(lang, []))

    def sandbox_complete(self, lang, prefix, session=None):
        return [prefix + "_live"]

    def sandbox_item_call(self, item_id):
        return {"lang": "tcl", "session": "bench", "file": "/x/b.tcl",
                "code": "source /x/b.tcl\nread 1\n",
                "unresolved": self.unresolved}

    def sandbox_scripts(self):
        return self.scripts

    def get_gd_vars(self):
        return {"bench_port": 1, "other": 2}


def check_sandbox():
    from gui import sandbox_syntax as syntax
    from gui.sandbox_presenter import (OWN_SESSION, SandboxPresenter,
                                       decode_state, encode_state)

    # --- Highlighting rules.
    def kinds(lang, line, state=syntax.NORMAL):
        spans, state = syntax.highlight_line(lang, line, state)
        return [(line[s:s + n], k) for s, n, k in spans], state

    got, state = kinds("python", "def f(): # c")
    if got != [("def", "keyword"), ("# c", "comment")]:
        fail(f"python highlighting: {got}")
    got, state = kinds("python", 'x = """a')
    if state != syntax.PY_TRIPLE_DOUBLE:
        fail("python multi-line string not carried to the next line")
    got, state = kinds("python", 'b""" + 2', state)
    if got != [('b"""', "string"), ("2", "number")] or state != syntax.NORMAL:
        fail(f"python multi-line string end: {got} {state}")
    got, state = kinds("lua", "--[[ note")
    if state != syntax.LUA_LONG_COMMENT:
        fail("lua long comment not carried to the next line")
    got, state = kinds("lua", ']] return tm.gd("a")', state)
    if got != [("]]", "comment"), ("return", "keyword"), ("tm.gd", "api"),
               ('"a"', "string")]:
        fail(f"lua highlighting: {got}")
    got, state = kinds("tcl", 'set x "a $y"; # note')
    if got != [("set", "keyword"), ('"a $y"', "string"),
               (" # note", "comment")]:
        fail(f"tcl highlighting: {got}")
    got, state = kinds("tcl", "tm::setgd k $::ns::v")
    if got != [("tm::setgd", "api"), ("$::ns::v", "variable")]:
        fail(f"tcl api/variable highlighting: {got}")

    # --- Completion helpers.
    if syntax.completion_prefix("python", "x = os.pa") != "os.pa" \
            or syntax.completion_prefix("tcl", "puts $::fo") != "$::fo" \
            or syntax.completion_prefix("python", "f(") != "":
        fail("completion prefix extraction broken")
    if syntax.gd_prefix("python", "tm.gd('be") != "be" \
            or syntax.gd_prefix("tcl", "[tm::gd be") != "be" \
            or syntax.gd_prefix("lua", "tm.gd") is not None:
        fail("tm.gd context detection broken")
    if syntax.merge_completions("a", ["ab", "b", "a"], ["ac", "ab"]) \
            != ["ab", "ac"]:
        fail("completion merge broken")
    if syntax.language_of("/x/y.LUA") != "lua" \
            or syntax.language_of("/x/y.txt") is not None:
        fail("language by extension broken")

    # --- Persisted state.
    lang, buffers = decode_state(encode_state("tcl", {"tcl": "puts %s\n"}))
    if lang != "tcl" or buffers != {"tcl": "puts %s\n"}:
        fail("sandbox state round trip broken")
    if decode_state("garbage") != ("python", {}):
        fail("invalid sandbox state not replaced by the defaults")

    # --- Presenter.
    view = FakeSandboxView()
    service = FakeSandboxService()
    saved = []
    p = SandboxPresenter(
        view, lambda: service,
        load_state=lambda: encode_state("tcl", {"tcl": "set a 1"}),
        save_state=saved.append)
    p.start()
    if view.lang != "tcl" or view.text != "set a 1" \
            or view.state != (True, False):
        fail(f"sandbox start: {view.lang} {view.text!r} {view.state}")

    p.refresh_sessions()
    if view.sessions != ([OWN_SESSION, "bench"], OWN_SESSION):
        fail(f"sandbox sessions: {view.sessions}")
    p.on_session_changed("bench")
    p.run()
    if service.calls[-1] != ("run", "tcl", "set a 1", "bench") \
            or view.state != (True, True) or not saved:
        fail(f"sandbox run: {service.calls} {view.state}")
    p.run()
    if len([c for c in service.calls if c[0] == "run"]) != 1:
        fail("a second run was sent while a script is running")
    p.on_event({"event": "output", "text": "hello\n"})
    p.on_event({"event": "finished", "result": 4, "error": None})
    if view.output[-2:] != [("output", "hello\n"), ("result", "4\n")] \
            or view.state != (True, False):
        fail(f"sandbox events: {view.output} {view.state}")
    p.on_event({"event": "finished", "result": None, "error": "boom\n"})
    if view.output[-1] != ("error", "boom\n"):
        fail(f"sandbox error event: {view.output[-1]}")

    # Reset of an attached context asks first.
    view.confirm_answer = False
    p.reset()
    if ("reset", "tcl", "bench") in service.calls or view.confirm_calls != 1:
        fail("context reset done without confirmation")
    view.confirm_answer = True
    p.reset()
    if service.calls[-1] != ("reset", "tcl", "bench"):
        fail(f"context reset not sent: {service.calls[-1]}")

    # A context that disappeared falls back to the own session.
    service.contexts = {}
    p.refresh_sessions()
    if p.session() is not None or view.sessions != ([OWN_SESSION],
                                                    OWN_SESSION):
        fail(f"vanished context kept: {p.session()} {view.sessions}")

    # A refused run is reported, the panel stays ready.
    service.refuse = "The sandbox is available when the run is stopped"
    p.run()
    if view.output[-1][0] != "error" or view.state != (True, False):
        fail(f"refused run: {view.output[-1]} {view.state}")
    service.refuse = None

    # Language change keeps one text per language.
    view.text = "set a 2"
    p.on_language_changed("lua")
    view.text = "x = 1"
    p.on_language_changed("tcl")
    if view.text != "set a 2":
        fail(f"text of a language lost on switch: {view.text!r}")

    # Files: open by extension, modified flag, save, export.
    script = os.path.join(WORK, "bench.lua")
    with open(script, "w", encoding="utf-8") as f:
        f.write("return 1\n")
    p.open_file(script)
    if view.lang != "lua" or view.text != "return 1\n" \
            or view.file != ("bench.lua", script) or p.is_modified():
        fail(f"open file: {view.lang} {view.text!r} {view.file}")
    view.text = "return 2\n"
    if not p.is_modified():
        fail("edited file not seen as modified")
    calls = view.confirm_calls
    view.confirm_answer = False
    p.open_file(script)
    if view.text != "return 2\n" or view.confirm_calls != calls + 1:
        fail("unsaved changes discarded without confirmation")
    view.confirm_answer = True
    service.scripts = {"lua": [script]}
    calls = view.confirm_calls
    if not p.save() or view.confirm_calls != calls + 1:
        fail("save of a test script did not ask for confirmation")
    with open(script, encoding="utf-8") as f:
        if f.read() != "return 2\n" or p.is_modified():
            fail("save did not write the file")
    view.save_path = os.path.join(WORK, "export")
    if not p.save_as() or not os.path.isfile(view.save_path + ".lua"):
        fail("save as did not add the language extension")

    # Item of the tree: language, context and code come from the item.
    service.contexts = {"tcl": ["bench"]}
    if not p.send_item(7) or view.lang != "tcl" \
            or view.text != "source /x/b.tcl\nread 1\n" \
            or p.session() != "bench" or view.file != ("", ""):
        fail(f"send item: {view.lang} {view.text!r} {p.session()}")

    # Variables not defined yet are named in the output.
    service.unresolved = ["test_path"]
    view.text = "keep me"
    p.send_item(7)
    if view.output[-1][0] != "error" \
            or "$(test_path)" not in view.output[-1][1]:
        fail(f"unresolved variables not reported: {view.output[-1]}")
    if view.text != "keep me":
        fail("editor replaced by a call with unresolved variables")
    service.unresolved = []

    # Completion: test variables inside tm::gd, else static and live names.
    p.complete("set v [tm::gd be")
    if view.completions != ("be", ["bench_port"]):
        fail(f"gd completion: {view.completions}")
    p.complete("tm::s")
    if view.completions != ("tm::s", ["tm::s_live", "tm::setgd", "tm::str"]):
        fail(f"name completion: {view.completions}")
    p.complete("puts (")
    if view.completions != ("", []):
        fail(f"completion without prefix: {view.completions}")

    # Unloaded test: panel disabled, back to the own session.
    p.set_loaded(False)
    if view.state != (False, False):
        fail(f"panel state without test: {view.state}")


def main():
    log_path = os.path.join(WORK, "logs", "run.log")
    view = FakeView(log_path)
    sched = FakeScheduler()
    service = FakeService()
    q = queue.Queue()
    rp = RunPresenter(view, sched, lambda: service, q)

    if rp.state is not TestState.IDLE:
        fail("initial state not IDLE")

    # Start: RUNNING, log file created, execute sent.
    rp.on_start_test()
    if rp.state is not TestState.RUNNING:
        fail("start did not enter RUNNING")
    if view.log_file_name != log_path or not os.path.isfile(log_path):
        fail(f"log file not opened at {log_path!r} "
             f"(got {view.log_file_name!r})")
    if ("execute",) not in service.calls:
        fail(f"execute not sent: {service.calls}")

    # Output queue drained into the view and the log file.
    q.put("hello")
    sched.tick("run_poll")
    if "hello" not in view.log_lines:
        fail("output line did not reach the view")

    # Pause / resume.
    rp.on_start_test()
    if rp.state is not TestState.PAUSED or ("pause",) not in service.calls:
        fail("pause did not work")
    if not view.ui_states or view.ui_states[-1].steps_enabled is not True:
        fail("steps not enabled while paused")
    sched.tick("pause_flip")
    if view.start_actions[-1][1] not in ("pause", "pause2"):
        fail(f"pause flip icon: {view.start_actions[-1]}")
    rp.on_start_test()
    if rp.state is not TestState.RUNNING or ("cont",) not in service.calls:
        fail("resume did not work")

    # Stop: the first request passes, a second one needs confirmation.
    rp.on_stop_test()
    if service.calls.count(("stop",)) != 1 or view.confirm_calls != 0:
        fail("first stop was not sent without confirmation")
    rp.on_stop_test()
    if service.calls.count(("stop",)) != 1 or view.confirm_calls != 1:
        fail("second stop sent although refused")
    view.confirm_abort = True
    rp.on_stop_test()
    if service.calls.count(("stop",)) != 2 or view.confirm_calls != 2:
        fail("second stop not sent although confirmed")

    # Finish, failed verdict: exit code 1, back to IDLE.
    view.succeeded = False
    rp.on_run_finished()
    if rp.state is not TestState.IDLE:
        fail("finish did not return to IDLE")
    if rp.run_exit_code != 1:
        fail(f"exit code {rp.run_exit_code}, expected 1")
    if os.path.isfile(log_path + "-1.saved") or view.sink is not None:
        fail("log sink not detached cleanly")

    # Second run rotates the first log to -1.saved; a new run forgets
    # the previous stop.
    view.succeeded = True
    rp.on_start_test()
    if not os.path.isfile(log_path + "-1.saved"):
        fail("previous log was not rotated to -1.saved")
    rp.on_stop_test()
    if service.calls.count(("stop",)) != 3 or view.confirm_calls != 2:
        fail("stop of a new run asked for confirmation")
    rp.on_run_finished()
    if rp.run_exit_code != 0:
        fail(f"exit code {rp.run_exit_code}, expected 0")

    # step_into from IDLE arms the step then starts, ending PAUSED.
    service.calls.clear()
    rp.on_step_into()
    if rp.state is not TestState.PAUSED:
        fail("step_into from idle did not end PAUSED")
    if service.calls[0] != ("step_into",):
        fail(f"step not armed first: {service.calls[:2]}")

    # run-and-close.
    rp.runandclose = True
    rp.on_run_finished()
    if not view.closed:
        fail("runandclose did not close the window")

    # File presenter: recent-files LRU and cross-presenter broadcast.
    from gui.file_presenter import FilePresenter

    class FakeFileView:
        def __init__(self):
            self.recent = None

        def update_recent_files(self, files):
            self.recent = list(files)

        def set_variables_service(self, service):
            pass

    fv1, fv2 = FakeFileView(), FakeFileView()
    fp1 = FilePresenter(fv1, None, [], {}, max_recent=3)
    fp2 = FilePresenter(fv2, None, [], {}, max_recent=3)
    for name in ("/a.tum", "/b.tum", "/c.tum", "/d.tum", "/b.tum"):
        fp1.add_file_to_recent(name)
    expected = ["/b.tum", "/d.tum", "/c.tum"]
    if fv1.recent != expected or fv2.recent != expected:
        fail(f"recent LRU: {fv1.recent} / {fv2.recent}, "
             f"expected {expected}")

    # Variables presenter: rows, filter, edition parsing, expr errors.
    from gui.variables_presenter import VariablesPresenter, parse_value

    class FakeVarsView:
        def __init__(self):
            self.rows = []      # list of (key, display) in row order
            self.hidden = {}
            self.expr = None

        def set_enabled(self, enabled):
            pass

        def clear_rows(self):
            self.rows.clear()

        def insert_row(self, row):
            self.rows.insert(row, None)

        def remove_row(self, row):
            del self.rows[row]

        def set_row(self, row, key, display, tooltip, value, editable):
            self.rows[row] = (key, display)

        def set_row_hidden(self, row, hidden):
            self.hidden[row] = hidden

        def row_display(self, row):
            return self.rows[row][1]

        def show_expr_result(self, text, is_error):
            self.expr = (text, is_error)

    vview = FakeVarsView()
    vsvc = FakeService()
    vp = VariablesPresenter(vview, lambda: vsvc)
    vp.var_updated("a", 1)
    vp.var_updated("b", {"x": 1})
    vp.var_updated("a", 2)
    if [r[0] for r in vview.rows] != ["a", "b"] or vview.rows[0][1] != "2":
        fail(f"variables rows: {vview.rows}")
    vp.var_deleted("a")
    vp.var_updated("c", "text")
    if [r[0] for r in vview.rows] != ["b", "c"]:
        fail(f"variables rows after delete: {vview.rows}")
    vp.set_filter("b")
    if vview.hidden.get(1) is not True or vview.hidden.get(0) is not False:
        fail(f"variables filter: {vview.hidden}")
    vp.edit_value("c", "[1, 2]")
    if ("set_gd_var", "c", [1, 2]) not in vsvc.calls:
        fail(f"edit parse: {vsvc.calls[-1]}")
    if parse_value("not a literal") != "not a literal":
        fail("parse_value fallback")

    # Tree state format: structural keys, snapshot round-trip, restore.
    from gui.tree_presenter import (walk_with_keys, snapshot_states,
                                    states_by_key, restore_states)

    class Node:
        def __init__(self, test_type, name, node_id, children=()):
            self.test_type = test_type
            self.name = name
            self.id = node_id
            self.kids = list(children)

    s1 = Node("step", "s", 11)
    s2 = Node("step", "s", 12)          # same (type, name): occurrence 1
    grp = Node("group", "g", 10, [s1, s2])
    root = Node("", "", 0, [grp])
    walk = lambda: walk_with_keys(root, lambda n: n.kids,
                                  lambda n: (n.test_type, n.name or ""))
    keys = [key for _n, key in walk()]
    if keys[1][-1] != ("step", "s", 0) or keys[2][-1] != ("step", "s", 1):
        fail(f"occurrence keys: {keys}")
    per_node = {10: (False, True, True, None),
                11: (True, False, True, "x > 1"),
                12: (False, True, True, None)}
    states = snapshot_states(walk(), lambda n: per_node[n.id])
    if states_by_key(states)[keys[1]] != (True, False, True, "x > 1"):
        fail("snapshot round-trip lost a state")
    # Entries saved before bp_condition existed load with condition None.
    if states_by_key([[[["step", "s", 0]], True, True, True]]) \
            [(("step", "s", 0),)] != (True, True, True, None):
        fail("length-tolerant decode broken")

    class FakeTreeService:
        def __init__(self):
            self.calls = []

        def get_skipped_state(self, node_id):
            return node_id == 12

        def set_enabled_state(self, node_id, state, unitary=False):
            self.calls.append(("enable", node_id, state, unitary))

        def add_breakpoint(self, node_id, condition=None):
            self.calls.append(("bp", node_id, condition))

    tsvc = FakeTreeService()
    applied = []
    restore_states(
        states, walk(), tsvc, True,
        set_folded=lambda n, folded: applied.append(("fold", n.id, folded)),
        show_skipped=lambda n: applied.append(("skipped", n.id)),
        set_checked=lambda n, checked: applied.append(("check", n.id, checked)),
        # Node 10 refuses breakpoints: no service re-issue for it.
        set_breakpoint=lambda n, condition: n.id != 10)
    if ("skipped", 12) not in applied or ("check", 12, True) in applied:
        fail(f"skipped node not handled: {applied}")
    if ("enable", 11, False, True) not in tsvc.calls:
        fail(f"enabled state not re-issued: {tsvc.calls}")
    if ("bp", 11, "x > 1") not in tsvc.calls:
        fail(f"breakpoint not re-issued: {tsvc.calls}")
    # Skip only affects check/enable: the breakpoint is still re-issued.
    if ("bp", 12, None) not in tsvc.calls:
        fail(f"breakpoint dropped on a skipped node: {tsvc.calls}")
    if any(c[0] == "bp" and c[1] == 10 for c in tsvc.calls):
        fail("breakpoint re-issued for a node that refuses breakpoints")

    # Tree view model: precedences, search rule, tables.
    from gui import tree_view_model as tvm

    if tvm.highlight_style(True, True) != "run" \
            or tvm.highlight_style(False, True) != "search" \
            or tvm.highlight_style(False, False) is not None:
        fail("highlight precedence broken")
    if tvm.gutter_icon(True, True, None) != "attach_bp" \
            or tvm.gutter_icon(True, False, None) != "attach" \
            or tvm.gutter_icon(False, True, "x") != "bp_conditional" \
            or tvm.gutter_icon(False, True, None) != "bp" \
            or tvm.gutter_icon(False, False, None) is not None:
        fail("gutter precedence broken")
    if not tvm.matches_search("cons", ["type"], "step1", "Console", None) \
            or tvm.matches_search("cons", ["name"], "step1", "Console", None):
        fail("search match rule broken")
    if not tvm.ITEM_CONFIG["unittest"].get("no_breakpoint") \
            or tvm.ITEM_CONFIG["Console"].get("unfoldable") is not False:
        fail("ITEM_CONFIG behavioral columns changed")
    cols = tvm.make_columns()
    if len({c['index'] for c in cols.values()}) != len(cols):
        fail("column indices not unique")

    # Status presenter: engine status decoding, failure state, follow.
    from gui.status_presenter import StatusPresenter
    from interpreter.test_items.test_result import TestValue

    sp = StatusPresenter()
    upd = sp.decode({'id': 5, 'status': 'started', 'timestamp': 42})
    if upd.highlight is not True or upd.follow or upd.paused:
        fail(f"started decode: {upd}")
    if sp.timestamp(5) != 42:
        fail("timestamp not latched")
    sp.decode({'id': 5, 'status': 'started', 'timestamp': 99})
    if sp.timestamp(5) != 42:
        fail("timestamp latch must keep the first value")
    upd = sp.decode({'id': 5, 'value': TestValue.SUCCESS.value,
                     'message': 'ok'})
    if upd.icon != "success" or upd.result != ("ok", "ok"):
        fail(f"success decode: {upd}")
    upd = sp.decode({'id': 5, 'value': TestValue.FAILURE.value,
                     'message': 'boom\nline2', 'date': 'D1'})
    if (upd.icon != "fail" or upd.failure_count != 1
            or upd.result != ("boom line2", "boom\nline2")):
        fail(f"failure decode: {upd}")
    if sp.global_success:
        fail("failure did not clear global success")
    if sp.history.entries(5) != [("D1", "boom\nline2")]:
        fail(f"failure history: {sp.history.entries(5)}")
    upd = sp.decode({'id': 5, 'value': TestValue.SUCCESS.value})
    if upd.icon != "success_after_fail":
        fail(f"success after failure: {upd.icon}")
    upd = sp.decode({'id': 5, 'value': TestValue.NORUN.value,
                     'message': 'skip'})
    if upd.icon is not None:
        fail(f"norun must not set an icon: {upd.icon}")
    upd = sp.decode({'id': 5, 'status': 'paused'})
    if not upd.paused or upd.highlight is not None:
        fail(f"paused decode: {upd}")
    upd = sp.decode({'id': 5, 'status': 'ended'})
    if upd.highlight is not False:
        fail(f"ended must reset the highlight: {upd}")
    if sp.decode({'id': 0, 'status': 'started'}) is not None:
        fail("id 0 must decode to None")
    sp.follow = True
    upd = sp.decode({'id': 6, 'status': 'started', 'timestamp': 1})
    if not upd.follow:
        fail("follow directive missing")
    # Follow target: topmost collapsed ancestor, else the item itself.
    if StatusPresenter.follow_target("it", [("p", True), ("gp", True)]) != "it":
        fail("expanded chain must target the item")
    if StatusPresenter.follow_target(
            "it", [("p", False), ("gp", False), ("root", True)]) != "gp":
        fail("target must be the topmost collapsed ancestor")
    sp.clear_run_marks()
    upd = sp.decode({'id': 5, 'value': TestValue.SUCCESS.value})
    if upd.icon != "success" or sp.history.current(5) != "":
        fail("clear_run_marks did not reset the failure state")
    sp.reset()
    if sp.timestamp(5) != -1 or not sp.global_success:
        fail("reset did not clear timestamps and the verdict")

    # Debug presenter: menu availability, condition rule, output sync.
    from gui.debug_presenter import (DebugPresenter, item_menu_state,
                                     breakpoint_condition_change)
    from interpreter.utils.constants import TestItemType as cst

    py_func = cst.TYPE_PY_FUNCTION.item_name
    ms = item_menu_state(py_func, True, False, False, True, [py_func, "Group"])
    if not (ms.attach_enabled and ms.attach_checked and ms.condition_enabled
            and ms.jump_enabled):
        fail(f"menu state (py_func, paused): {ms}")
    ms = item_menu_state("Sleep", False, True, False, True,
                         ["Sleep", cst.TYPE_PARALLEL.item_name])
    if ms.attach_enabled or ms.condition_enabled or ms.jump_enabled:
        fail(f"menu state (parallel, no_breakpoint): {ms}")
    if item_menu_state("Sleep", False, False, True, True, ["Sleep"]) \
            .jump_enabled:
        fail("jump must be disabled on a skipped item")
    if item_menu_state("Sleep", False, False, False, False, ["Sleep"]) \
            .jump_enabled:
        fail("jump must require a paused run")
    if breakpoint_condition_change(False, "  x == 1 ") != "x == 1":
        fail("condition text not kept")
    if breakpoint_condition_change(True, "") is not None:
        fail("emptied condition must downgrade to a plain breakpoint")
    if breakpoint_condition_change(False, "  ") is not False:
        fail("empty condition without a breakpoint must change nothing")

    class FakeDebugView:
        def __init__(self):
            self.steps_visible = None
            self.checked = False
            self.messages = []

        def set_step_actions_visible(self, visible):
            self.steps_visible = visible

        def debug_output_checked(self):
            return self.checked

        def set_debug_output_checked(self, checked):
            self.checked = checked

        def show_transient_message(self, text):
            self.messages.append(text)

    dview = FakeDebugView()
    dsvc = FakeService()
    dp = DebugPresenter(dview, lambda: dsvc)
    dview.checked = True    # the toggle signal comes from the checked box
    dp.on_debug_output_toggled(True)
    if dview.steps_visible is not True \
            or ("set_gd_var", "test_debug", True) not in dsvc.calls:
        fail(f"debug output toggle: {dsvc.calls}")
    if prefs.settings.debug_output is not True:
        fail("debug output preference not stored")
    dp.sync_debug_output({"test_debug": False})
    if dview.checked is not False or dview.steps_visible is not False:
        fail("effective test_debug not reflected")
    dp.sync_debug_output({"test_debug": False})   # no change: no flicker
    from runtime.tum_except import ETUMRuntimeError

    class JumpFailService:
        def jump_to(self, item_id):
            raise ETUMRuntimeError("no jump")

    DebugPresenter(dview, lambda: JumpFailService()).jump_to(3)
    if not dview.messages or "no jump" not in dview.messages[-1]:
        fail(f"jump error not surfaced: {dview.messages}")

    # Preferences presenter: restore/store, dirty set, effect dispatch.
    from gui.preferences_presenter import (PreferencesPresenter, pref_fields,
                                           apply_preference_changes)

    class FakePrefView:
        def __init__(self):
            self.values = {}

        def field_value(self, key, ftype):
            return self.values[key.name]

        def set_field_value(self, key, ftype, value):
            self.values[key.name] = value

    pview = FakePrefView()
    pp = PreferencesPresenter(pview)
    pp.restore()
    if len(pview.values) != len(pref_fields()):
        fail("restore did not fill every field")
    time_key = prefs.settings.SettingsShowTimeColumn
    pview.values[time_key.name] = not pview.values[time_key.name]
    pp.store()
    if not pp.is_changed(time_key) \
            or pp.is_changed(prefs.settings.SettingsLogFontSize):
        fail("dirty set wrong after store")
    if prefs.settings.value(time_key) != pview.values[time_key.name]:
        fail("store did not persist the edited value")

    class FakeMainView:
        def __init__(self):
            self.verbs = []

        def __getattr__(self, name):
            return lambda: self.verbs.append(name)

    mview = FakeMainView()
    apply_preference_changes(pp, mview)
    if mview.verbs != ["apply_time_column_preference"]:
        fail(f"effect dispatch: {mview.verbs}")

    # Session presenter: startup decisions, layout migration, save.
    from gui.session_presenter import SessionPresenter, STATE_VERSION

    path, saved, is_cli = SessionPresenter.initial_log_config("run.log")
    if not (is_cli and saved and os.path.isabs(path)):
        fail(f"cli log config: {path}, {saved}, {is_cli}")
    prefs.settings.log_file = "/tmp/stored.log"
    path, saved, is_cli = SessionPresenter.initial_log_config("")
    if is_cli or path != "/tmp/stored.log":
        fail(f"stored log config: {path}, {is_cli}")
    if SessionPresenter.startup_file("/nonexistent/x.tum") is not None:
        fail("missing CLI file must not fall back")
    real = os.path.join(WORK, "recent.tum")
    open(real, "w").close()
    prefs.settings.recent_files = [real]
    if SessionPresenter.startup_file("") != real:
        fail("recent file not picked at startup")

    class FakeSessionView:
        def __init__(self, accept_state):
            self._accept = accept_state
            self.calls = []

        def __getattr__(self, name):
            def call(*a):
                self.calls.append(name)
                if name == "restore_state":
                    return self._accept
                if name == "save_geometry" or name == "save_state":
                    return b"blob"
            return call

    sview = FakeSessionView(False)
    SessionPresenter(sview).restore_layout()
    if "apply_default_layout" not in sview.calls:
        fail(f"unknown state blob must apply the default layout: {sview.calls}")
    sview = FakeSessionView(True)
    sp2 = SessionPresenter(sview)
    sp2.save("/tmp/t.tum")
    if not {"save_geometry", "save_state", "stash_file_state",
            "save_column_sizes"} <= set(sview.calls):
        fail(f"session save calls: {sview.calls}")
    sp2.restore_layout()
    if "apply_default_layout" in sview.calls:
        fail("accepted state blob must not reset the layout")
    if not isinstance(STATE_VERSION, int):
        fail("STATE_VERSION missing")

    # Open target: path resolution, marker, highlight tables.
    from gui import open_target

    if open_target.timestamp_marker(42) != "@@42@@":
        fail("timestamp marker format changed")
    rel = os.path.basename(real)
    if open_target.resolve_log_path(rel, WORK) != os.path.join(WORK, rel):
        fail("relative log path not joined to the test dir")
    if open_target.resolve_log_path("missing.txt", WORK) is not None:
        fail("missing path must resolve to None")
    rules = open_target.log_rules()
    if any(style not in open_target.LOG_STYLES for _e, style in rules):
        fail("log rule references an unknown style")
    for sample in ("/var/log/x.log", r"C:\Users\a\b.txt", "./rel/f.py"):
        if not open_target.FILE_PATTERN.search(sample):
            fail(f"file pattern misses {sample}")

    # Run I/O: message dispatch, line pump, tee guard.
    from gui import run_io

    routed = []
    for m in ({"type": "gd_update", "key": "k", "value": 1},
              {"type": "gd_delete", "key": "k"},
              {"id": None}, {"id": 3, "status": "started"}):
        run_io.dispatch_status(
            m,
            lambda k, v: routed.append(("up", k, v)),
            lambda k: routed.append(("del", k)),
            lambda: routed.append(("fin",)),
            lambda s: routed.append(("st", s["id"])))
    if routed != [("up", "k", 1), ("del", "k"), ("fin",), ("st", 3)]:
        fail(f"status dispatch: {routed}")

    class FakeStream:
        def read(self):
            return "a\n\nb\n"

    lines = []
    run_io.pump_lines(FakeStream(), lines.append)
    if lines != ["a", "b"]:
        fail(f"line pump: {lines}")

    class BadOut:
        def write(self, m):
            raise OSError("disk full")

    seen = []
    tee = run_io.LogTee(seen.append, BadOut())
    tee.writeln("x")
    if seen != ["x\n"]:
        fail("tee must survive a file-side write error")

    # Dialog presenter: argv, result protocol, last-value store.
    from interpreter.test_items.dialog_presenter import (
        arg_at, send_result, load_last, save_last)

    if arg_at(["a"], 1) is not None or arg_at(["a", "b"], 1) != "b":
        fail("arg_at broken")

    class FakeConn:
        def __init__(self):
            self.sent = None
            self.closed = False

        def send(self, v):
            self.sent = v

        def close(self):
            self.closed = True

    fc = FakeConn()
    send_result(fc, "res", False)
    if fc.sent != ["res", False] or not fc.closed:
        fail(f"send_result: {fc.sent}")
    if load_last("check", "none yet") != "":
        fail("load_last must default to ''")
    save_last("check", "dlg/1", "value1")
    if load_last("check", "dlg/1") != "value1":
        fail("last-value round-trip broken")
    save_last("check", "dlg/1", "")
    if load_last("check", "dlg/1") != "value1":
        fail("empty value must keep the previous one")

    # Choices tri-state transitions.
    from interpreter.test_items.dialog_choices_files.choices_presenter \
        import bulk_check_target, fold_action

    if bulk_check_target("checked") is not True \
            or bulk_check_target("unchecked") is not False \
            or bulk_check_target("partial") is not None:
        fail("bulk check transitions broken")
    if fold_action("unchecked") != (False, "unchecked") \
            or fold_action("partial") != (True, "checked"):
        fail("fold transitions broken")

    check_sandbox()

    # PySide must never have been imported by this chain.
    if any(m.startswith("PySide") for m in sys.modules):
        fail("a PySide module was imported by the presenter chain")

    print("GUI PRESENTER CHECK: PASS")


if __name__ == "__main__":
    main()
