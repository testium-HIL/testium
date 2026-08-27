# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Web view (NiceGUI). Implements the RunView/FileView/VariablesView
surfaces of gui/protocols.py on top of the shared presenters.

The presenters mutate shared state only; each connected browser gets its
own page whose elements are synced from that state by a per-client
timer. Every client sees the same run."""

import html
import queue
import re
import sys
import threading

from nicegui import app, ui

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
from web_win.scheduler import NiceScheduler

# Item icon name (tree_view_model.ITEM_CONFIG) -> Material icon.
_TYPE_ICON = {
    "folder.png": "folder", "folder-open.png": "folder",
    "folder-orange.png": "folder_special",
    "folder-open-orange.png": "folder_special",
    "document.png": "description", "pytest.png": "science",
    "terminal.png": "terminal", "cycle.png": "loop",
    "python.png": "code", "lua.png": "code", "report.png": "summarize",
    "git.png": "device_hub", "plot.png": "show_chart",
    "image.png": "image", "info.png": "info", "let.png": "edit_note",
    "verif.png": "rule", "note.png": "edit_note", "question.png": "help",
    "sleep.png": "bedtime", "label.png": "label", "run.png": "play_circle",
    "json.png": "data_object", "parallel.png": "alt_route",
    "parallel_branch.png": "alt_route",
}
_STATUS_ICON = {
    "success": ("check_circle", "positive"),
    "success_after_fail": ("check_circle", "orange"),
    "fail": ("cancel", "negative"),
}
_LIGHT_COLOR = {"green": "green", "red": "red", "gray": "grey"}
_MAX_LOG_LINES = 20000

_TREE_HEADER_SLOT = '''
<div class="row items-center no-wrap q-gutter-x-xs" style="min-height: 22px">
  <q-icon v-if="props.node.bp" name="circle" color="red" size="10px"/>
  <q-icon v-else name="circle" color="transparent" size="10px"/>
  <q-icon :name="props.node.ticon" size="16px" class="text-grey-5"/>
  <span :class="props.node.name_class">{{ props.node.name }}</span>
  <q-icon v-if="props.node.status_icon" :name="props.node.status_icon"
          :color="props.node.status_color" size="15px"/>
  <q-badge v-if="props.node.failures" color="red" rounded>
    {{ props.node.failures }}</q-badge>
  <span v-if="props.node.result"
        class="text-grey-6 text-caption ellipsis"
        style="max-width: 20em">{{ props.node.result }}</span>
</div>
'''


def _compiled_log_rules():
    """(regex, CSS style) pairs from the shared open_target tables."""
    rules = []
    for exp, name in open_target.log_rules():
        color, flags = open_target.LOG_STYLES[name]
        style = f"color: {color.lower()};"
        if "bold" in flags:
            style += " font-weight: bold;"
        if "italic" in flags:
            style += " font-style: italic;"
        if "small" in flags:
            style = "color: #555; font-size: 70%;"
        rules.append((re.compile(exp), style))
    return rules


class _NodeRef:
    """tree_presenter node adapter over the tree node dicts."""

    def __init__(self, node):
        self.node = node
        self.id = node["id"]

    @property
    def children(self):
        return [_NodeRef(c) for c in self.node["children"]]


class WebView:
    def __init__(self, test_file, config_files, runandclose, log_file,
                 defines, report, report_type, report_pattern):
        self._start_file = test_file
        self._runandclose = runandclose
        self._report_file = locate_report_file(report)
        self._report_type = report_type
        self._report_pattern = report_pattern

        env_init()
        from multiprocessing import Queue as MpQueue
        self.status_queue = MpQueue()
        self.threads_queue = queue.Queue()

        self.session = SessionPresenter(self)
        self._file_states = FileStateStore()
        self._log_file_name, self._log_saved, _cli = \
            self.session.initial_log_config(log_file)

        # Shared state, read by the per-client sync timers.
        self._nodes = {}          # interpreter id -> node dict
        self._roots = []
        self._expanded = set()
        self._ticked = set()
        self._tree_dirty = False
        self._tree_version = 0
        self._log_lines = []      # pre-rendered HTML lines
        self._log_total = 0
        self._log_generation = 0
        self._log_rules = _compiled_log_rules()
        self._var_rows = []
        self._vars_dirty = False
        self._vars_version = 0
        self._light = "green"
        self._elapsed = ""
        self._running = False
        self._steps_enabled = False
        self._paused_icon = False
        self._file_path = ""
        self._captured = []
        self._captured_lock = threading.Lock()
        self._status = StatusPresenter()

        self.scheduler = NiceScheduler()
        self.runner = RunPresenter(self, self.scheduler,
                                   lambda: self.file_manager.test_service,
                                   self.threads_queue)
        self.runner.runandclose = runandclose
        self.file_manager = FilePresenter(
            self, self.status_queue, config_files, defines)
        self.variables = VariablesPresenter(
            self, lambda: self.file_manager.test_service)

        self.runner.set_blink_green()

        # Kept for messages that must reach the terminal: everything else
        # is captured into the web log panel below.
        self._console = sys.stdout
        self.stream = StringQueue()
        stdio_redir.redirect(self.stream)
        self.out_log = run_io.LogTee(self._buffer_captured)
        stdio_redir.redirect(self.out_log)

        app.timer(0.1, self._pump_output)
        app.timer(0.1, self._pump_status)
        app.timer(0.3, self._flush_pending)
        app.on_startup(self._on_startup)
        app.on_shutdown(self._on_shutdown)
        ui.page("/")(self._page)

    def console(self, text):
        try:
            self._console.write(text + "\n")
            self._console.flush()
        except Exception:
            pass

    def _on_startup(self):
        self.console("Testium web interface on http://localhost:8080 "
                     "(Ctrl+C to stop)")
        start_file = self.session.startup_file(self._start_file)
        if start_file and self.file_manager.load(start_file):
            self.restore_file_state()
        if self._runandclose:
            self.runner.on_start_test()

    def _on_shutdown(self):
        self.file_manager.clear_process()
        stdio_redir.restore()

    # --- per-client page ----------------------------------------------------

    def _page(self):
        ui.dark_mode().enable()
        selection = {"id": None}

        def on_select(e):
            selection["id"] = e.value

        def toggle_breakpoint():
            self._toggle_breakpoint(selection["id"])

        with ui.header().classes(
                "items-center bg-grey-10 q-py-xs q-px-md"):
            light = ui.icon("circle", color="green", size="14px") \
                .classes("q-mr-sm")
            start_button = ui.button(icon="play_arrow",
                                     on_click=self.runner.on_start_test) \
                .props("flat round").tooltip("Run / pause")
            stop_button = ui.button(icon="stop",
                                    on_click=self.runner.on_stop_test) \
                .props("flat round").tooltip("Stop")
            ui.separator().props("vertical").classes("q-mx-sm")
            step_buttons = [
                ui.button(icon="redo", on_click=self.runner.on_step_over)
                .props("flat round").tooltip("Step over"),
                ui.button(icon="arrow_downward",
                          on_click=self.runner.on_step_into)
                .props("flat round").tooltip("Step into"),
                ui.button(icon="arrow_upward",
                          on_click=self.runner.on_step_out)
                .props("flat round").tooltip("Step out"),
            ]
            ui.separator().props("vertical").classes("q-mx-sm")
            ui.button(icon="fiber_manual_record", on_click=toggle_breakpoint) \
                .props("flat round color=red").tooltip(
                    "Breakpoint on the selected item")
            ui.space()
            elapsed_label = ui.label("").classes(
                "text-h6 text-weight-light q-mr-md")
            file_label = ui.label("").classes("text-grey-5 text-caption")

        with ui.splitter(value=38).classes("w-full") \
                .style("height: calc(100vh - 60px)") as splitter:
            with splitter.before:
                with ui.column().classes("w-full h-full q-pa-sm"):
                    ui.label("TEST SET").classes(
                        "text-caption text-grey-6 q-pl-xs")
                    with ui.scroll_area().classes("w-full h-full"):
                        tree = ui.tree([], node_key="id", label_key="name",
                                       tick_strategy="strict",
                                       on_select=on_select,
                                       on_tick=self._on_tick,
                                       on_expand=self._on_expand) \
                            .props("dense no-connectors")
                        tree.add_slot("default-header", _TREE_HEADER_SLOT)
            with splitter.after:
                with ui.column().classes("w-full h-full q-pa-sm"):
                    with ui.row().classes("items-center w-full q-pl-xs"):
                        ui.label("LOG").classes("text-caption text-grey-6")
                        ui.space()
                        follow = ui.checkbox("Follow", value=True) \
                            .props("dense size=xs").classes(
                                "text-caption text-grey-6")
                    log_area = ui.scroll_area().classes(
                        "w-full font-mono rounded-borders") \
                        .style("height: 58%; background: #16181d; "
                               "font-size: 12px; line-height: 1.25")
                    with log_area:
                        log_box = ui.column().classes("w-full q-pa-xs gap-0")
                    ui.label("VARIABLES").classes(
                        "text-caption text-grey-6 q-pl-xs")
                    table = ui.table(
                        columns=[
                            {"name": "name", "label": "name",
                             "field": "name", "align": "left",
                             "sortable": True},
                            {"name": "value", "label": "value",
                             "field": "value", "align": "left"},
                        ],
                        rows=[], row_key="name") \
                        .props("dense flat bordered virtual-scroll") \
                        .classes("w-full").style("height: 32%")

        state = {"log_idx": 0, "log_gen": -1, "tree_v": -1, "vars_v": -1}

        def sync():
            if state["log_gen"] != self._log_generation:
                state["log_gen"] = self._log_generation
                state["log_idx"] = 0
                log_box.clear()
            start = self._log_total - len(self._log_lines)
            if state["log_idx"] < self._log_total:
                new = self._log_lines[max(0, state["log_idx"] - start):]
                state["log_idx"] = self._log_total
                with log_box:
                    ui.html("<br>".join(new) or "&nbsp;").classes(
                        "whitespace-pre")
                if follow.value:
                    log_area.scroll_to(percent=1.0)
            if state["tree_v"] != self._tree_version:
                state["tree_v"] = self._tree_version
                tree._props["nodes"] = self._roots
                tree._props["ticked"] = sorted(self._ticked)
                tree._props["expanded"] = sorted(self._expanded)
                tree.update()
            if state["vars_v"] != self._vars_version:
                state["vars_v"] = self._vars_version
                table.rows = [{"name": k, "value": v}
                              for k, v, _t in self._var_rows]
                table.update()
            light.props(
                f"color={_LIGHT_COLOR.get(self._light, 'grey')}")
            start_button.props(
                f"icon={'pause' if self._paused_icon else 'play_arrow'}")
            if self._running:
                stop_button.enable()
            else:
                stop_button.disable()
            for b in step_buttons:
                if self._steps_enabled:
                    b.enable()
                else:
                    b.disable()
            elapsed_label.set_text(self._elapsed)
            file_label.set_text(self._file_path)

        ui.timer(0.3, sync)

    # --- pumps (server-side, state only) ------------------------------------

    def _pump_output(self):
        try:
            run_io.pump_lines(self.stream, self.threads_queue.put)
        except Exception:
            pass

    def _pump_status(self):
        while not self.status_queue.empty():
            run_io.dispatch_status(
                self.status_queue.get(),
                self.variables.var_updated,
                self.variables.var_deleted,
                self.runner.on_run_finished,
                self._update_status)

    def _buffer_captured(self, text):
        with self._captured_lock:
            self._captured.append(text)

    def _flush_pending(self):
        with self._captured_lock:
            captured, self._captured = self._captured, []
        if captured:
            self.append_log("".join(captured))
        if self._vars_dirty:
            self._vars_dirty = False
            self._vars_version += 1
        if self._tree_dirty:
            self._tree_dirty = False
            for node in self._nodes.values():
                self._decorate(node)
            self._tree_version += 1

    # --- tree ---------------------------------------------------------------

    @staticmethod
    def _decorate(node):
        """Display fields consumed by the tree header slot."""
        cfg = tree_view_model.ITEM_CONFIG.get(node["type"], {})
        node["ticon"] = _TYPE_ICON.get(cfg.get("icon", ""), "circle")
        icon, color = _STATUS_ICON.get(node["icon"], (None, None))
        node["status_icon"] = icon
        node["status_color"] = color
        style = tree_view_model.highlight_style(node["running"], False)
        if style == "run":
            node["name_class"] = \
                "bg-green-3 text-black q-px-xs rounded-borders"
        elif node["skipped"]:
            node["name_class"] = "text-strike text-grey-6"
        else:
            node["name_class"] = ""

    def _make_nodes(self, test_set_item):
        nodes = []
        for test_id in test_set_item.keys():
            item = test_set_item[test_id]
            cfg = tree_view_model.ITEM_CONFIG.get(item["type"], {})
            node = {
                "id": item["id"], "type": item["type"],
                "name": item["name"],
                "no_breakpoint": bool(cfg.get("no_breakpoint")),
                "checked": True, "bp": False, "bp_condition": None,
                "skipped": False, "running": False,
                "icon": None, "failures": 0, "result": "",
                "children": self._make_nodes(item["child"]),
            }
            self._decorate(node)
            self._nodes[item["id"]] = node
            self._ticked.add(item["id"])
            if not item["folded"]:
                self._expanded.add(item["id"])
            nodes.append(node)
        return nodes

    def _update_status(self, status):
        if status.get('id', 0) <= 0:
            return
        node = self._nodes.get(status['id'])
        if node is None:
            return
        upd = self._status.decode(status)
        if upd.icon is not None:
            node["icon"] = upd.icon
        if upd.failure_count is not None:
            node["failures"] = upd.failure_count
        if upd.result is not None:
            node["result"] = upd.result[0]
        if upd.highlight is True:
            node["running"] = True
        elif upd.highlight is False:
            node["running"] = False
        self._tree_dirty = True
        if upd.paused:
            self.runner.on_paused()

    def _on_expand(self, e):
        self._expanded = set(e.value or [])

    def _on_tick(self, e):
        service = self.file_manager.test_service
        new = set(e.value or [])
        changed = new ^ self._ticked
        self._ticked = new
        if service is None:
            return
        for item_id in changed:
            service.set_enabled_state(item_id, item_id in new)
        self._sync_enabled()

    def _sync_enabled(self):
        service = self.file_manager.test_service
        states = service.get_enabled_states()
        self._ticked = {i for i in self._nodes
                        if states.get(i, True)}
        for item_id, node in self._nodes.items():
            node["checked"] = states.get(item_id, True)
        self._tree_dirty = True

    def _toggle_breakpoint(self, item_id):
        node = self._nodes.get(item_id)
        service = self.file_manager.test_service
        if node is None or service is None or node["no_breakpoint"]:
            return
        node["bp"] = not node["bp"]
        node["bp_condition"] = None
        if node["bp"]:
            service.add_breakpoint(node["id"])
        else:
            service.del_breakpoint(node["id"])
        self._tree_dirty = True

    def _mark_skipped(self, nodes, service, force=False):
        for node in nodes:
            skipped = force or service.get_skipped_state(node["id"])
            node["skipped"] = skipped
            self._mark_skipped(node["children"], service, force=skipped)
        self._tree_dirty = True

    # --- RunView implementation (driven by gui/run_presenter.py) ------------

    def apply_run_ui(self, state):
        self._running = state.running
        self._steps_enabled = state.steps_enabled

    def set_start_action(self, text, icon):
        self._paused_icon = icon.startswith("pause")

    def set_status_light(self, color):
        self._light = color

    def set_elapsed(self, text):
        self._elapsed = text

    def append_log(self, text):
        lines = text.splitlines()
        self._log_lines.extend(self._line_html(line) for line in lines)
        self._log_total += len(lines)
        del self._log_lines[:-_MAX_LOG_LINES]

    def _line_html(self, line):
        """Colorize with the shared open_target rules (last match wins,
        like the Qt highlighter)."""
        styles = [None] * len(line)
        for pattern, style in self._log_rules:
            for match in pattern.finditer(line):
                for i in range(*match.span()):
                    styles[i] = style
        parts = []
        i = 0
        while i < len(line):
            j = i
            while j < len(line) and styles[j] == styles[i]:
                j += 1
            chunk = html.escape(line[i:j])
            if styles[i]:
                parts.append(f'<span style="{styles[i]}">{chunk}</span>')
            else:
                parts.append(chunk)
            i = j
        return "".join(parts)

    def clear_log(self):
        self._log_lines = []
        self._log_total = 0
        self._log_generation += 1

    def show_transient_message(self, text):
        try:
            ui.notify(text)
        except Exception:
            self.append_log(text)

    def can_start(self):
        return self.file_manager.test_service is not None

    def test_file(self):
        return self.file_manager.test_file

    def log_config(self):
        return (self._log_file_name, self._log_saved)

    def set_log_file_name(self, path):
        self._log_file_name = path

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
        for node in self._nodes.values():
            node.update(icon=None, failures=0, result="")
        self._tree_dirty = True

    def clear_current_marks(self):
        for node in self._nodes.values():
            node["running"] = False
        self._tree_dirty = True

    def run_succeeded(self):
        return self._status.global_success

    def close_window(self):
        app.shutdown()

    # --- FileView implementation (driven by gui/file_presenter.py) ----------

    def begin_load(self):
        pass

    def set_load_phase(self, text):
        pass

    def pump(self):
        pass

    def end_load(self):
        pass

    def show_loaded_test(self, test_data, gd_vars, test_dir):
        self._nodes.clear()
        self._ticked.clear()
        self._expanded.clear()
        self._status.reset()
        self._roots = self._make_nodes(test_data)
        self._mark_skipped(self._roots, self.file_manager.test_service)
        self.variables.load_initial_vars(gd_vars)
        self._tree_dirty = True

    def show_load_failure(self):
        self.show_transient_message("No test file could be loaded")

    def set_window_file(self, path):
        self._file_path = path

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

    # --- tree state persistence (shared format, gui/tree_presenter.py) ------

    def _walk_with_keys(self):
        root = {"id": 0, "type": "", "name": "", "children": self._roots}
        return tree_presenter.walk_with_keys(
            _NodeRef(root),
            lambda ref: ref.children,
            lambda ref: (ref.node["type"], ref.node["name"] or ""))

    def snapshot_tree_states(self):
        return tree_presenter.snapshot_states(
            self._walk_with_keys(), lambda ref: (
                ref.id not in self._expanded,
                ref.node["checked"],
                ref.node["bp"],
                ref.node["bp_condition"]))

    def restore_tree_states(self, states):
        def set_folded(ref, folded):
            if folded:
                self._expanded.discard(ref.id)
            else:
                self._expanded.add(ref.id)

        def show_skipped(ref):
            ref.node["skipped"] = True
            self._expanded.discard(ref.id)

        def set_checked(ref, checked):
            ref.node["checked"] = checked

        def set_breakpoint(ref, condition):
            if ref.node["no_breakpoint"]:
                return False
            ref.node["bp"] = True
            ref.node["bp_condition"] = condition
            return True

        tree_presenter.restore_states(
            states, self._walk_with_keys(),
            self.file_manager.test_service, True,
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

    # --- VariablesView implementation (gui/variables_presenter.py) ----------

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

    # --- SessionView (only the pieces the web view persists) -----------------

    def save_column_sizes(self):
        pass


def WebMain(
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
    view = WebView(test_file, config_files, run, log_file, defines,
                   report, report_type, report_pattern)
    try:
        ui.run(title="Testium", reload=False, show=not run,
               uvicorn_logging_level="warning")
    except BaseException:
        # The streams are captured: restore them so the failure is visible.
        stdio_redir.restore()
        raise
    exit_code = view.runner.run_exit_code
    sys.exit(exit_code if exit_code >= 0 else 0)
