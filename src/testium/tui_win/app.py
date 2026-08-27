# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Terminal view (Textual). Implements the RunView/FileView/VariablesView
surfaces of gui/protocols.py on top of the shared presenters."""

import queue
import re
import sys
import threading
import time

from rich.text import Text
from textual.app import App
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, RichLog, Static, Tree

import interpreter.utils.settings as prefs
from interpreter.utils.test_init import env_init, locate_report_file
from gui import open_target, run_io, tree_presenter, tree_view_model
from gui.file_presenter import FilePresenter
from gui.run_presenter import RunPresenter
from gui.session_presenter import SessionPresenter
from gui.status_presenter import StatusPresenter
from gui.tree_presenter import FileStateStore
from gui.variables_presenter import VariablesPresenter
from runtime.stdout_redirect import stdio_redir
from runtime.string_queue import StringQueue
from tui_win.scheduler import TextualScheduler

# Item icon name (tree_view_model.ITEM_CONFIG) -> glyph.
_GLYPHS = {
    "folder.png": "▸", "folder-open.png": "▸",
    "folder-orange.png": "▹", "folder-open-orange.png": "▹",
    "cycle.png": "↻", "terminal.png": ">_", "python.png": "py",
    "lua.png": "lua", "pytest.png": "pt", "document.png": "·",
    "parallel.png": "≡", "parallel_branch.png": "≡",
}
_STATUS_MARK = {
    "success": ("✔", "green"),
    "success_after_fail": ("✔", "dark_orange"),
    "fail": ("✘", "red"),
}
_GUTTER_MARK = {
    "bp": ("●", "red"), "bp_conditional": ("◌", "red"),
    "attach": ("◆", "blue"), "attach_bp": ("◆", "red"),
}
_LIGHT = {"green": "green", "red": "red", "gray": "grey50"}


def _rich_log_rules():
    """Compile open_target.log_rules() to (regex, rich style) pairs."""
    styles = {}
    for name, (color, flags) in open_target.LOG_STYLES.items():
        style = color.lower()
        if "bold" in flags:
            style += " bold"
        if "italic" in flags:
            style += " italic"
        if "small" in flags:
            style = "grey35"
        styles[name] = style
    return [(re.compile(exp), styles[name])
            for exp, name in open_target.log_rules()]


class _NodeRef:
    """tree_presenter node adapter: exposes .id over a Textual TreeNode."""

    def __init__(self, node):
        self.node = node
        self.id = node.data["id"] if node.data else 0

    @property
    def children(self):
        return [_NodeRef(c) for c in self.node.children]


class TestiumApp(App):
    CSS = """
    #tree { width: 1fr; }
    #right { width: 1fr; }
    #log { height: 2fr; border-top: solid $accent; }
    #vars { height: 1fr; }
    #status { dock: bottom; height: 1; background: $panel; }
    """
    BINDINGS = [
        Binding("f5,s", "start", "Run/Pause"),
        Binding("f6,x", "stop", "Stop"),
        Binding("o", "step_over", "Step over"),
        Binding("i", "step_into", "Step into"),
        Binding("u", "step_out", "Step out"),
        Binding("space,b", "breakpoint", "Breakpoint", priority=True),
        Binding("c", "toggle_check", "Enable/disable item"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, test_file, config_files, runandclose, log_file,
                 defines, report, report_type, report_pattern, debug,
                 status_queue=None):
        super().__init__()
        # Created before Textual rearranges the standard streams: the
        # multiprocessing resource tracker spawn fails afterwards.
        if status_queue is None:
            from multiprocessing import Queue as MpQueue
            status_queue = MpQueue()
        self.status_queue = status_queue
        self._start_file = test_file
        self._runandclose = runandclose
        self._cli_log_file = log_file
        self._report_file = locate_report_file(report)
        self._report_type = report_type
        self._report_pattern = report_pattern
        self._config_files = config_files
        self._defines = defines
        self._debug = debug

        self.threads_queue = queue.Queue()
        self._item_nodes = {}          # interpreter id -> TreeNode
        self._log_rules = _rich_log_rules()
        self._running = False
        self._steps_enabled = False
        self._light = "green"
        self._elapsed = ""
        self._start_icon = "start"
        self._var_rows = []       # [(key, display, tooltip)]
        self._captured = []
        self._captured_lock = threading.Lock()
        self._vars_dirty = False
        self._dirty_nodes = set()
        self._follow_node = None
        self._stop_threads = False
        self.run_exit_code = -1

    # --- layout -----------------------------------------------------------

    def compose(self):
        yield Horizontal(
            Tree("test set", id="tree"),
            Vertical(
                RichLog(id="log", highlight=False, markup=False,
                        max_lines=100000),
                DataTable(id="vars"),
                id="right"),
        )
        yield Static(id="status")
        yield Footer()

    def on_mount(self):
        self.title = "Testium"
        self.test_tree = self.query_one("#tree", Tree)
        self.log_view = self.query_one("#log", RichLog)
        self.vars_table = self.query_one("#vars", DataTable)
        self.vars_table.add_columns("name", "value")
        self.test_tree.show_root = False

        env_init()
        self.session = SessionPresenter(self)
        self._file_states = FileStateStore()
        self._log_file_name, self._log_saved, _cli = \
            self.session.initial_log_config(self._cli_log_file)

        self.scheduler = TextualScheduler(self)
        self.runner = RunPresenter(self, self.scheduler,
                                   lambda: self.file_manager.test_service,
                                   self.threads_queue)
        self.runner.runandclose = self._runandclose
        self.file_manager = FilePresenter(
            self, self.status_queue, self._config_files, self._defines)
        self.variables = VariablesPresenter(
            self, lambda: self.file_manager.test_service)
        self._status = StatusPresenter()
        self.runner.set_blink_green()

        self._ui_thread = threading.get_ident()
        # Parent stdout -> stream -> line pump -> threads_queue; the
        # presenter drains it into the log view and the log file.
        self.stream = StringQueue()
        stdio_redir.redirect(self.stream)
        threading.Thread(target=self._output_loop, daemon=True).start()
        self.out_log = run_io.LogTee(self._emit_captured)
        stdio_redir.redirect(self.out_log)
        threading.Thread(target=self._status_loop, daemon=True).start()

        self.set_interval(0.3, self._flush_pending)
        start_file = self.session.startup_file(self._start_file)
        if start_file and self.file_manager.load(start_file):
            self.restore_file_state()
        self._refresh_status_bar()
        if self._runandclose:
            self.runner.on_start_test()

    def on_unmount(self):
        self._stop_threads = True
        self.run_exit_code = self.runner.run_exit_code
        self.file_manager.clear_process()
        stdio_redir.restore()

    # --- background threads ----------------------------------------------

    def _output_loop(self):
        while not self._stop_threads:
            try:
                run_io.pump_lines(self.stream, self.threads_queue.put)
            except Exception:
                pass
            time.sleep(0.1)

    def _emit_captured(self, text):
        # Tee display path; capture threads buffer, the UI timer flushes.
        if threading.get_ident() == self._ui_thread:
            self.append_log(text)
            return
        with self._captured_lock:
            self._captured.append(text)

    def _status_loop(self):
        # One UI hop per batch: per-message call_from_thread round-trips
        # made the tree lag minutes behind the log on busy runs.
        while not self._stop_threads:
            batch = []
            while not self.status_queue.empty():
                batch.append(self.status_queue.get())
            if batch:
                try:
                    self.call_from_thread(self._dispatch_batch, batch)
                except Exception:
                    return
            time.sleep(0.1)

    def _dispatch_batch(self, batch):
        self._dirty_nodes = set()
        self._follow_node = None
        for m in batch:
            run_io.dispatch_status(
                m,
                self.variables.var_updated,
                self.variables.var_deleted,
                self.runner.on_run_finished,
                self._update_status)
        for node in self._dirty_nodes:
            self._render_node(node)
        if self._follow_node is not None:
            ancestors = []
            parent = self._follow_node.parent
            while parent is not None and parent is not self.test_tree.root:
                ancestors.append((parent, parent.is_expanded))
                parent = parent.parent
            target = StatusPresenter.follow_target(
                self._follow_node, ancestors)
            self.test_tree.scroll_to_node(target)

    # --- tree -------------------------------------------------------------

    def _populate(self, parent, test_set_item):
        for test_id in test_set_item.keys():
            item = test_set_item[test_id]
            data = {
                "id": item["id"], "type": item["type"],
                "name": item["name"], "doc": item["doc"],
                "checked": True, "bp": False, "bp_condition": None,
                "skipped": False, "running": False,
                "icon": None, "failures": 0, "result": "",
            }
            cfg = tree_view_model.ITEM_CONFIG.get(item["type"], {})
            data["no_breakpoint"] = bool(cfg.get("no_breakpoint"))
            node = parent.add("", data=data,
                              expand=not item["folded"],
                              allow_expand=len(item["child"]) > 0)
            self._item_nodes[item["id"]] = node
            self._render_node(node)
            if len(item["child"]) > 0:
                self._populate(node, item["child"])

    def _render_node(self, node):
        d = node.data
        label = Text()
        kind = tree_view_model.gutter_icon(
            False, d["bp"], d["bp_condition"])
        mark, style = _GUTTER_MARK.get(kind, (" ", ""))
        label.append(mark + " ", style)
        label.append("[x] " if d["checked"] else "[ ] ", "dim")
        cfg = tree_view_model.ITEM_CONFIG.get(d["type"], {})
        label.append(_GLYPHS.get(cfg.get("icon", ""), "·") + " ", "dim")
        name_style = ""
        if d["running"]:
            name_style = "black on " + tree_view_model.RUN_BG
        elif d["skipped"]:
            name_style = "dim strike"
        label.append(d["name"], name_style)
        if d["icon"] in _STATUS_MARK:
            mark, style = _STATUS_MARK[d["icon"]]
            label.append(" " + mark, style)
        if d["failures"]:
            label.append(f" {d['failures']}F", "red")
        if d["result"]:
            label.append("  " + d["result"], "dim")
        node.set_label(label)

    def _update_status(self, status):
        if status.get('id', 0) <= 0:
            return
        node = self._item_nodes.get(status['id'])
        if node is None:
            return
        upd = self._status.decode(status)
        d = node.data
        if upd.icon is not None:
            d["icon"] = upd.icon
        if upd.failure_count is not None:
            d["failures"] = upd.failure_count
        if upd.result is not None:
            d["result"] = upd.result[0]
        if upd.highlight is True:
            d["running"] = True
        elif upd.highlight is False:
            d["running"] = False
        self._dirty_nodes.add(node)
        if upd.follow:
            self._follow_node = node
        if upd.paused:
            self.runner.on_paused()

    def _mark_skipped(self, parent, service):
        for child in parent.children:
            skipped = service.get_skipped_state(child.data["id"])
            child.data["skipped"] = skipped
            if skipped:
                child.collapse()
                self._mark_subtree_skipped(child)
            else:
                self._mark_skipped(child, service)
            self._render_node(child)

    def _mark_subtree_skipped(self, parent):
        for child in parent.children:
            child.data["skipped"] = True
            self._render_node(child)
            self._mark_subtree_skipped(child)

    def _sync_enabled(self):
        service = self.file_manager.test_service
        states = service.get_enabled_states()
        for item_id, node in self._item_nodes.items():
            node.data["checked"] = states.get(item_id, True)
            self._render_node(node)

    # --- actions ----------------------------------------------------------

    def action_start(self):
        if self.file_manager.test_service is not None:
            self.runner.on_start_test()

    def action_stop(self):
        if self._running:
            self.runner.on_stop_test()

    def action_step_over(self):
        self.runner.on_step_over()

    def action_step_into(self):
        self.runner.on_step_into()

    def action_step_out(self):
        self.runner.on_step_out()

    def action_breakpoint(self):
        node = self.test_tree.cursor_node
        service = self.file_manager.test_service
        if node is None or node.data is None or service is None:
            return
        d = node.data
        if d["no_breakpoint"]:
            return
        d["bp"] = not d["bp"]
        d["bp_condition"] = None
        if d["bp"]:
            service.add_breakpoint(d["id"])
        else:
            service.del_breakpoint(d["id"])
        self._render_node(node)

    def action_toggle_check(self):
        node = self.test_tree.cursor_node
        service = self.file_manager.test_service
        if node is None or node.data is None or service is None:
            return
        checked = not node.data["checked"]
        service.set_enabled_state(node.data["id"], checked)
        self._sync_enabled()

    # --- RunView implementation (driven by gui/run_presenter.py) ----------

    def apply_run_ui(self, state):
        self._running = state.running
        self._steps_enabled = state.steps_enabled
        self._refresh_status_bar()

    def set_start_action(self, text, icon):
        self._start_icon = icon
        self._refresh_status_bar()

    def set_status_light(self, color):
        self._light = color
        self._refresh_status_bar()

    def set_elapsed(self, text):
        self._elapsed = text
        self._refresh_status_bar()

    def append_log(self, text):
        for line in text.splitlines() or [""]:
            rich = Text(line)
            for pattern, style in self._log_rules:
                for match in pattern.finditer(line):
                    rich.stylize(style, *match.span())
            self.log_view.write(rich)

    def clear_log(self):
        self.log_view.clear()

    def show_transient_message(self, text):
        self.notify(text)

    def can_start(self):
        return self.file_manager.test_service is not None \
            and not self._running

    def test_file(self):
        return self.file_manager.test_file

    def log_config(self):
        return (self._log_file_name, self._log_saved)

    def set_log_file_name(self, path):
        self._log_file_name = path
        self._refresh_status_bar()

    def report_config(self):
        return (self._report_file, self._report_type, self._report_pattern)

    def attach_log_sink(self, handle):
        self.out_log.set(handle)

    def detach_log_sink(self):
        self.out_log.reset()

    def read_captured(self):
        return self.stream.read()

    def reset_run_marks(self):
        self._status.clear_run_marks()
        self._status.global_success = True
        for node in self._item_nodes.values():
            node.data.update(icon=None, failures=0, result="")
            self._render_node(node)

    def clear_current_marks(self):
        for node in self._item_nodes.values():
            if node.data["running"]:
                node.data["running"] = False
                self._render_node(node)

    def run_succeeded(self):
        return self._status.global_success

    def close_window(self):
        self.exit()

    # --- FileView implementation (driven by gui/file_presenter.py) --------

    def begin_load(self):
        pass

    def set_load_phase(self, text):
        pass

    def pump(self):
        pass

    def end_load(self):
        pass

    def show_loaded_test(self, test_data, gd_vars, test_dir):
        self.test_tree.clear()
        self._item_nodes.clear()
        self._status.reset()
        self._populate(self.test_tree.root, test_data)
        self._mark_skipped(self.test_tree.root, self.file_manager.test_service)
        self.variables.load_initial_vars(gd_vars)

    def show_load_failure(self):
        self.notify("No test file could be loaded", severity="error")

    def set_window_file(self, path):
        self.title = "Testium - " + path

    def update_recent_files(self, files):
        pass

    def set_variables_service(self, service):
        self.variables.set_available(service is not None)
        if service is None:
            self.clear_rows()

    def begin_tree_swap(self):
        pass

    def end_tree_swap(self):
        pass

    # --- tree state persistence (shared format, gui/tree_presenter.py) ----

    def _walk_with_keys(self):
        root = _NodeRef(self.test_tree.root)
        return tree_presenter.walk_with_keys(
            root,
            lambda ref: ref.children,
            lambda ref: (ref.node.data["type"], ref.node.data["name"] or ""))

    def snapshot_tree_states(self):
        return tree_presenter.snapshot_states(
            self._walk_with_keys(), lambda ref: (
                not ref.node.is_expanded,
                ref.node.data["checked"],
                ref.node.data["bp"],
                ref.node.data["bp_condition"]))

    def restore_tree_states(self, states):
        service = self.file_manager.test_service

        def set_breakpoint(ref, condition):
            if ref.node.data["no_breakpoint"]:
                return False
            ref.node.data["bp"] = True
            ref.node.data["bp_condition"] = condition
            self._render_node(ref.node)
            return True

        def set_checked(ref, checked):
            ref.node.data["checked"] = checked
            self._render_node(ref.node)

        def set_folded(ref, folded):
            ref.node.collapse() if folded else ref.node.expand()

        def show_skipped(ref):
            ref.node.data["skipped"] = True
            ref.node.collapse()
            self._render_node(ref.node)

        tree_presenter.restore_states(
            states, self._walk_with_keys(), service, True,
            set_folded=set_folded, show_skipped=show_skipped,
            set_checked=set_checked, set_breakpoint=set_breakpoint)
        self._sync_enabled()

    def stash_file_state(self, path):
        self._file_states.stash(path, self.snapshot_tree_states(),
                                self._log_file_name, self._log_saved)

    def restore_file_state(self):
        entry = self._file_states.restore(self.file_manager.test_file)
        if entry is None:
            return
        states, log_path, log_saved = entry
        if log_path:
            self._log_file_name = log_path
            self._log_saved = bool(log_saved)
        self.restore_tree_states(states)

    # --- VariablesView implementation (gui/variables_presenter.py) --------

    def set_enabled(self, enabled):
        pass

    def clear_rows(self):
        self._var_rows = []
        self._vars_dirty = True

    def insert_row(self, row):
        self._var_rows.insert(row, ("", "", ""))

    def remove_row(self, row):
        del self._var_rows[row]
        self._vars_dirty = True

    def set_row(self, row, key, display, tooltip, value, editable):
        self._var_rows[row] = (key, display, tooltip)
        self._vars_dirty = True

    def set_row_hidden(self, row, hidden):
        pass

    def row_display(self, row):
        return self._var_rows[row][1]

    def _flush_pending(self):
        with self._captured_lock:
            captured, self._captured = self._captured, []
        if captured:
            self.append_log("".join(captured))
        # Debounced: a rebuild per gd update stalled the interface.
        if not self._vars_dirty:
            return
        self._vars_dirty = False
        self.vars_table.clear()
        for key, display, _tooltip in self._var_rows:
            self.vars_table.add_row(key, display)

    # --- SessionView (only the pieces the TUI persists) --------------------

    def save_column_sizes(self):
        pass

    # --- status bar --------------------------------------------------------

    def _refresh_status_bar(self):
        text = Text()
        text.append(" ● ", _LIGHT.get(self._light, "grey50"))
        state = ("paused" if self._steps_enabled
                 else "running" if self._running else "idle")
        text.append(state, "bold")
        if self._elapsed:
            text.append("  " + self._elapsed)
        if self._log_file_name:
            text.append("  log: " + self._log_file_name, "dim")
        self.query_one("#status", Static).update(text)


def TuiMain(
    test_file=None,
    config_files="",
    run=False,
    log_file="",
    defines="",
    report="",
    report_type="",
    report_pattern=[],
    debug=False,
):
    app = TestiumApp(test_file, config_files, run, log_file, defines,
                     report, report_type, report_pattern, debug)
    app.run()
    exit_code = app.run_exit_code if app.run_exit_code >= 0 else 0
    sys.exit(exit_code)
