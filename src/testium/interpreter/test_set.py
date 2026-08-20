import os
import datetime
from queue import Queue
from interpreter.utils.params import expanse
import api.testium as tm
from runtime.tum_except import ETUMSyntaxError, ETUMError
import interpreter.utils.settings as prefs
from interpreter.test_report.test_report import TestReport
from interpreter.utils.py_func_exec import PyFuncExecEngine
from interpreter.utils.api_srv import api_request
from interpreter.utils import bins
from interpreter.utils import step_ctrl
from interpreter.utils.step_ctrl import StepController
from runtime.tum_except import ETUMRuntimeError
from interpreter.utils.constants import TestItemType as cst_type
import interpreter.utils.constants as cst
from interpreter.utils.constants import TEST_TYPE_LIST
from interpreter.test_items.test_item import test_data
from interpreter.test_items.item_actions import TestItemActions
from interpreter.test_items.test_result import TestValue


def _build_item_path(item) -> str:
    """Build a breadcrumb path like 'main > Group > sub-group' from an item to root."""
    parts = []
    current = item
    while current is not None:
        name = current.name()
        parts.append(name if name else f"[{current.type()}]")
        current = current.parent()
    return " > ".join(reversed(parts))


def _flatten_actions(actions, out, parent_seq_name):
    """Expand nested lists and included ``sequence`` entries into ``out`` as a
    flat list of single test-item dicts, propagating each sequence's source
    filename onto its items.

    Replaces the previous approach, which spliced each entry into the step
    list and rebuilt the whole list every time (O(n^2) over the step list, and
    a rebuild that duplicated entries when a nested list held more than one
    element). This single forward pass is linear.
    """
    for idx, action in enumerate(actions):
        # a bare list raises its elements to the same level
        if isinstance(action, (list, tuple)):
            _flatten_actions(action, out, parent_seq_name)
            continue
        # a NoneType (e.g. pointing at an unused alias) contributes nothing
        if action is None:
            continue
        # a 'sequence' (an included file) is spliced in, with its filename
        # propagated onto each of its items
        if isinstance(action, dict) and "sequence" in action:
            sequence = action["sequence"]["data"]
            f = action["sequence"]["filename"]
            if isinstance(sequence, dict):
                sequence = [{k: v} for k, v in sequence.items()]
            # Case of an empty sequence
            elif sequence is None:
                tm.print_info(
                    f"An empty sequence is loaded in '{parent_seq_name}'."
                )
                sequence = []
            elif not isinstance(sequence, list):
                raise ETUMSyntaxError(
                    f"Syntax error in '{parent_seq_name}' step number {idx+1}. Sequence definition: '{str(action)}'",
                    f
                )
            if not isinstance(sequence, list):
                raise ETUMSyntaxError(
                    f"Invalid included sequence in '{parent_seq_name}' "
                    f"(step {idx+1}): expected a list of steps, got "
                    f"{type(sequence).__name__}.",
                    f
                )
            for s in sequence:
                # Propagate the source filename onto each included step. Only a
                # single-key mapping with a mapping body can carry it; malformed
                # entries are left untouched and reported by the loader below,
                # with their real location.
                if isinstance(s, dict) and len(s) == 1:
                    body = s[next(iter(s))]
                    if isinstance(body, dict):
                        body["seq_filename"] = f
            _flatten_actions(sequence, out, parent_seq_name)
            continue

        out.append(action)


class TestSet:
    def __init__(
        self,
        tum_fime: str,
        test_dict: dict,
        status_queue: Queue,
    ):
        self._test_file = tum_fime
        self.post_exec_file = None

        self._report = None
        self._success = False
        self.status_queue = status_queue
        self.report_path = ""
        self.report_type = ""
        self.report_pattern = []
        self._testdict = test_dict
        self._step_ctrl = StepController()

        self._tree = self.__loadTestTree(tum_fime)
        self.__setStepControllerRecursively(self._rootItem)
        self._rootItem.step_ctrl = self._step_ctrl
        self.dict_report = self._testdict.get("report", None)
        self.set_post_exec()
        self._validate_runtime_deps()

    def _validate_runtime_deps(self):
        """Resolve external interpreters needed by this test tree and fail
        early with a clear message if any is missing.

        Python is always required (the eval engine always runs). Lua is
        only required when at least one ``lua_func`` item is present.
        """
        needed = ["python"]
        if self.__has_item_type(self._rootItem, cst_type.TYPE_LUA_FUNCTION):
            needed.append("lua")
        bins.ensure(*needed)

    def __has_item_type(self, parent, item_type):
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.type() == item_type.item_name:
                return True
            if self.__has_item_type(child, item_type):
                return True
        return False

    def execute(self):
        self._report = TestReport(self.dict_report)
        report_header = {
            cst.DB_TEST_FILE: os.path.abspath(self._test_file),
            cst.DB_TEST_SET_NAME: os.path.splitext(os.path.split(self._test_file)[1])[
                0
            ],
            cst.DB_TEST_REVISION: tm.gd("test_version"),
            cst.DB_SEQUENCER_VERSION: tm.gd("testium_version"),
            cst.DB_TESTRUN_DATE: tm.gd("testrun_date"),
            cst.DB_TESTRUN_TIME: tm.gd("testrun_time"),
        }
        if self.report_type != "":
            rep = TestReport.export_to_dict(
                self.report_type, "", self.report_path, self.report_pattern, []
            )
            self._report.exports = rep
        self._report.open(report_header)
        self.setReport()

        res = None
        try:
            # Clear _is_paused leftovers from a previous run (stop while
            # paused); the armed step is kept, see the finally comment.
            self._rootItem.cont()
            self.__contAllRecursively(self._rootItem)
            a_test_is_skipped = self.__aTestIsSkipped(self._rootItem)
            a_test_is_disabled = self.__aTestIsDisabled(self._rootItem)
            res = self._rootItem.execute()
        finally:
            # End-of-run cleanup of a still-armed step (e.g. step at the very
            # last item). Not done at start of run so a step_into sent from
            # IDLE (armed before 'execute' on the command thread) survives.
            if self._step_ctrl.reset():
                tm.print_warn("Jump target was not reached.")
            self._end_test_date = datetime.datetime.now()
            self._test_duration = self._end_test_date - tm.gd("start_test_date")

            # report ending
            d = {}
            if res is not None:
                self._success = res.test_result == TestValue.SUCCESS
                d.update({cst.DB_TEST_SET_RESULT: str(res.test_result)})
            d.update({cst.DB_TEST_SET_DURATION: self._test_duration})
            self._report.close(d)

            # updating global dict with report output
            outs = tm.gd("test_outputs", None)
            if outs is not None:
                outs.append(self._report.path)
            else:
                outs = [self._report.path]

            # test cleanup
            del self._report

            # updating global dict with outputs
            tm.setgd("test_outputs", outs)

            tm.cleanup_instances("console")
            tm.cleanup_instances("plot")

        if a_test_is_skipped or a_test_is_disabled:
            tm.print_warn("A test has been skipped or disabled in this test run.")

    def set_report(self, rep_path: str, rep_type: str, pattern: list):
        if rep_path != "":
            self.report_path = rep_path
        self.report_type = rep_type
        self.report_pattern = pattern

    def success(self) -> bool:
        "Returns if the test has been a success"
        return self._success

    def extractReportPath(self):
        r = ""
        if self.dict_report is None:
            return r

        n = self.dict_report.get("file_name", "")
        if n == "":
            return r

        n = expanse(n)

        f = expanse(self.dict_report.get("path", ""))
        if f == "":
            f = expanse(prefs.settings.report_path)

        if not os.path.isabs(f):
            f = os.path.abspath(f)
        if not os.path.exists(f):
            os.makedirs(f)

        f = os.path.join(f, n)
        return f

    def __stopRunningTestsRecursively(self, parent):
        for i in range(parent.childCount()):
            if parent.child(i).isRunning():
                parent.child(i).stop()
            self.__stopRunningTestsRecursively(parent.child(i))

    def stop(self):
        # A pending step or pause must not re-pause execute_on_stop cleanup
        # items.
        self._step_ctrl.disarm()
        self._step_ctrl.clear_pause()
        self._rootItem.stop()
        self.__stopRunningTestsRecursively(self._rootItem)

    def pause(self):
        # Run-level request: the current step finishes, the next one pauses
        # before its body. Items already running are past their pause point.
        self._step_ctrl.disarm()
        self._step_ctrl.request_pause()

    def __setReportRecursively(self, parent):
        for i in range(parent.childCount()):
            parent.child(i).report = self._report
            self.__setReportRecursively(parent.child(i))

    def setReport(self):
        self._rootItem.report = self._report
        self.__setReportRecursively(self._rootItem)

    def addBreakpoint(self, item_id, condition=None):
        item = self.__findItemById(item_id)
        item.addBreakpoint(condition)

    def delBreakpoint(self, item_id):
        item = self.__findItemById(item_id)
        item.delBreakpoint()

    def setDebugAttach(self, item_id, enabled):
        """Request (or cancel) a debugger attach on a py_func item, without
        the 'debug' attribute. Session only: not saved with the test."""
        item = self.__findItemById(item_id)
        if item.type() != cst_type.TYPE_PY_FUNCTION.item_name:
            raise ETUMRuntimeError(
                f"Debugger attach only applies to 'py_func' items, "
                f"'{item.name()}' is a '{item.type()}' item.")
        item.setDebugAttach(bool(enabled))

    def __contAllRecursively(self, parent):
        # All items, not only running ones: a finished item can hold an
        # orphaned _is_paused that would re-freeze its next execution.
        for i in range(parent.childCount()):
            parent.child(i).cont()
            self.__contAllRecursively(parent.child(i))

    def cont(self):
        self._step_ctrl.disarm()
        self._step_ctrl.clear_pause()
        self._step_ctrl.cancel_jump()
        self._rootItem.cont()
        self.__contAllRecursively(self._rootItem)

    def __setStepControllerRecursively(self, parent):
        for i in range(parent.childCount()):
            parent.child(i).step_ctrl = self._step_ctrl
            self.__setStepControllerRecursively(parent.child(i))

    def __step(self, mode):
        item = self._step_ctrl.step(mode)
        if item is not None:
            # Release only the item we step from; other paused items (e.g.
            # parallel branches) stay paused.
            item.cont()

    def __validateJump(self, target):
        """Common jump checks: run paused, target reachable, no parallel."""
        if self._step_ctrl.current() is None:
            raise ETUMRuntimeError(
                "Jump is only available while the run is paused on an item.")
        if target is None:
            raise ETUMRuntimeError("Jump target not found.")
        # A disabled or skipped node would never fire the arrival: the seek
        # would silently swallow the rest of the run.
        node = target
        while node is not None:
            if node.skipped or not node.enabled:
                raise ETUMRuntimeError(
                    f"Cannot jump to '{target.name()}': "
                    f"'{node.name()}' is unchecked or skipped.")
            if node.type() in (cst_type.TYPE_PARALLEL.item_name,
                               cst_type.TYPE_PARALLEL_BRANCH.item_name):
                raise ETUMRuntimeError(
                    "Cannot jump into or out of a parallel block.")
            node = node.parent()
        node = self._step_ctrl.current()
        while node is not None:
            if node.type() in (cst_type.TYPE_PARALLEL.item_name,
                               cst_type.TYPE_PARALLEL_BRANCH.item_name):
                raise ETUMRuntimeError(
                    "Cannot jump into or out of a parallel block.")
            node = node.parent()

    def __jumpNotice(self, verb, target):
        cycles = []
        node = target.parent()
        while node is not None:
            if node.type() == cst_type.TYPE_CYCLE.item_name:
                cycles.append(node.name())
            node = node.parent()
        msg = f'{verb} "{target.name()}".'
        if cycles:
            names = '", "'.join(reversed(cycles))
            msg += f' Cycle "{names}" restarts at iteration 1.'
        print(msg)

    def jumpTo(self, item_id):
        target = self.__findItemById(item_id)
        self.__validateJump(target)
        self.__jumpNotice("Jumping to", target)
        self._step_ctrl.disarm()
        self._step_ctrl.arm_jump(target)

    def jumpBack(self):
        target = self._step_ctrl.last_executed()
        if target is None:
            raise ETUMRuntimeError("No step has been executed yet.")
        self.__validateJump(target)
        self.__jumpNotice("Re-running", target)
        self._step_ctrl.disarm()
        # No pause on the target: it re-executes, the next item pauses.
        self._step_ctrl.arm_jump(target, pause_on_target=False)

    def __getEnabledStatesRecursively(self, parent, out):
        for i in range(parent.childCount()):
            child = parent.child(i)
            out[child.id()] = child.enabled
            self.__getEnabledStatesRecursively(child, out)

    def getEnabledStates(self):
        """Enabled state of every item, one round-trip: {id: enabled}."""
        out = {}
        self.__getEnabledStatesRecursively(self._rootItem, out)
        return out

    def step_into(self):
        self.__step(step_ctrl.MODE_INTO)

    def step_over(self):
        self.__step(step_ctrl.MODE_OVER)

    def step_out(self):
        self.__step(step_ctrl.MODE_OUT)

    def updateParentsState(self, child):
        parent = child.parent()
        if parent is not None:
            n = parent.childCount()
            all_unchecked = True
            one_checked = False
            for i in range(n):
                if parent.child(i).enabled:
                    all_unchecked = False
                else:
                    one_checked = True
            if (n > 0) and all_unchecked:
                parent.enabled = False
                self.updateParentsState(parent)

            elif n > 0:
                parent.enabled = True
                self.updateParentsState(parent)

    def __aTestIsSkipped(self, parent):
        res = False
        i = 0
        while (res is False) and (i < parent.childCount()):
            if parent.child(i).skipped:
                res = True
            i = i + 1

        i = 0
        while (res is False) and (i < parent.childCount()):
            res = self.__aTestIsSkipped(parent.child(i))
            i = i + 1

        return res

    def __aTestIsDisabled(self, parent):
        res = False
        i = 0
        while (res is False) and (i < parent.childCount()):
            if not parent.child(i).enabled:
                res = True
            i = i + 1

        i = 0
        while (res is False) and (i < parent.childCount()):
            res = self.__aTestIsDisabled(parent.child(i))
            i = i + 1

        return res

    def __findItemById(self, item_id, parent=None):
        if parent is None:
            parent = self._rootItem
        res = None
        i = 0
        while (res is None) and (i < parent.childCount()):
            if parent.child(i).id() == item_id:
                res = parent.child(i)
            i = i + 1

        i = 0
        while (res is None) and (i < parent.childCount()):
            res = self.__findItemById(item_id, parent.child(i))
            i = i + 1

        return res

    def isTestTypePresent(self, test_type: cst_type, parent=None):
        if parent is None:
            parent = self._rootItem
        res = False
        i = 0
        while (not res) and (i < parent.childCount()):
            if parent.child(i).type() == test_type.item_name:
                res = True
            i = i + 1

        i = 0
        while (not res) and (i < parent.childCount()):
            res = self.isTestTypePresent(test_type, parent.child(i))
            i = i + 1
        return res

    def getEnabledState(self, item_id):
        """Return True if the item is enabled, False otherwise."""
        item = self.__findItemById(item_id)
        return item.enabled

    def getSkippedState(self, item_id):
        """Return True if the item is skipped, False otherwise."""
        item = self.__findItemById(item_id)
        return item.skipped

    def getItemDoc(self, item_id):
        item = self.__findItemById(item_id)
        return item.doc()

    def getFolded(self, item_id):
        item = self.__findItemById(item_id)
        return item.is_folded

    def setEnabledState(self, item_id, enabled_state, unitary=False):
        """Set the item_id item enabled attributes to enabled_state."""
        parent = self.__findItemById(item_id)
        parent.enabled = enabled_state
        if not unitary:
            for i in range(parent.childCount()):
                parent.child(i).enabled = enabled_state
                self.enableDisableAll(parent.child(i), enabled_state)
            self.updateParentsState(parent)

    def checkUncheckAll(self, checked: bool):
        self.enableDisableAll(self._rootItem, checked)

    def enableDisableAll(self, parent, enabled_state):
        """If enabled_state, enable all the child of parent item, else disable them."""
        if enabled_state:
            for i in range(parent.childCount()):
                parent.child(i).enabled = True
                self.enableDisableAll(parent.child(i), enabled_state)
        else:
            for i in range(parent.childCount()):
                parent.child(i).enabled = False
                self.enableDisableAll(parent.child(i), enabled_state)

    def __loadTestTree(self, filename):
        try:
            dict_main = self._testdict["main"]
        except:
            raise ETUMSyntaxError(
                f"the 'main' root item of the principal 'tum' file could not be found.",
                filename
            )

        self._rootItem = (cst_type.TYPE_ROOT.item_class)(
            dict_item=dict_main, status_queue=self.status_queue
        )
        try:
            ret = self.load_test_recursively(self._rootItem, dict_main, filename)
        except ETUMError:
            # Already a located, user-readable testium error.
            raise
        except Exception as e:
            # Last-resort net: turn any unforeseen failure into a located error
            # rather than a bare traceback / 'crashed for any reason'.
            raise ETUMSyntaxError(
                f"Unexpected error while building the test tree: "
                f"{type(e).__name__}: {e}",
                filename
            ) from e
        self.set_post_exec()
        return ret

    def set_post_exec(self):
        post_exec = self._testdict.get("post_execution", None)
        if post_exec is None:
            self.post_exec_file = None
            return

        postexec_file = post_exec["file_name"]

        if not os.path.isfile(os.path.join(tm.gd("test_directory"), postexec_file)):
            raise ETUMSyntaxError(f"Post execution file '{postexec_file}' not found")

        self.post_exec_file = postexec_file

    def run_post_exec(self):
        tm.print_debug("Is there a post execution file ?")
        post_exec_file = self.post_exec_file
        test_dir = tm.gd("test_directory")

        if post_exec_file is None:
            post_exec_file = os.path.join(test_dir, "post_execution.py")

        if not os.path.isfile(post_exec_file):
            tm.print_info(f"No post exec in this test.")
            tm.print_debug(f'  No file: "{post_exec_file}".')
            return

        proc = PyFuncExecEngine(api_request, 10)
        # start the process for executing external python
        proc.start()
        try:
            if not proc.wait_ready(10):
                raise ETUMRuntimeError(
                    f"""Impossible to start the external python execution process.
    Is the python path correct ?
    python_bin = {tm.gd("python_bin", "no python path defined")}"""
                )
            tm.print_debug(f'Post-execution from: "{post_exec_file}"')
            if self.rootItem().result.success:
                # tests backup is done here
                succ, res = proc.func_call(post_exec_file, "post_exec", [])
                if not succ == TestValue.SUCCESS:
                    tm.print_warn(
                        f"Test success but the \"post_exec\" function failed: {res}"
                    )
            else:
                succ, res = proc.func_call(post_exec_file, "post_exec_fail", [])
                if not succ == TestValue.SUCCESS:
                    tm.print_warn(
                        f"Test failed but the \"post_exec_fail\" function failed: {res}"
                    )
        finally:
            proc.stop()
            proc.join()

    def rootItem(self):
        return self._rootItem

    def _load_item(self, item):
        """Run an item's self-load, deferring a failure (e.g. a missing module)
        to a run-time FAILURE instead of aborting the whole test load."""
        try:
            return item.load()
        except Exception as e:
            msg = getattr(e, "_message", None) or str(e)
            item._load_error = msg
            tm.print_warn(
                f"'{item.cmd()}' item '{item.name()}' could not be loaded: "
                f"{msg} (it will FAIL at run)."
            )
            return {}

    def load_test_recursively(self, tree_parent, parent_seq, file_name):
        ret = {}
        path = _build_item_path(tree_parent)
        if not isinstance(parent_seq, dict):
            raise ETUMSyntaxError(
                f"In: {path}\n"
                f"The body of '{tree_parent.cmd()}' must be a mapping (with a "
                f"'steps' list) but is {type(parent_seq).__name__} "
                f"({parent_seq!r}).",
                file_name
            )
        try:
            parent_seq_name = parent_seq["name"]
        except KeyError:
            parent_seq["name"] = "sequence"
            parent_seq_name = "sequence"
        try:
            parent_seq_actions = parent_seq["steps"]
        except KeyError:
            raise ETUMSyntaxError(
                f"In: {path}\n"
                f"No 'steps' list found for the '{tree_parent.cmd()}' item "
                f"'{parent_seq_name}'.\n"
                f"A container item must declare its children under 'steps:'.",
                file_name
            )
        # if action is a dictionary , we assume it is a single action
        # that has not been nested in a list, so do it
        if isinstance(parent_seq_actions, (dict)):
            parent_seq_actions = [parent_seq_actions]
        # an empty 'steps:' (None) is a valid, empty sequence
        if parent_seq_actions is None:
            parent_seq_actions = []
        if not isinstance(parent_seq_actions, (list, tuple)):
            raise ETUMSyntaxError(
                f"In: {path}\n"
                f"The 'steps' of '{parent_seq_name}' must be a list of test "
                f"items but is {type(parent_seq_actions).__name__} "
                f"({parent_seq_actions!r}).",
                file_name
            )
        test_dir = tm.gd("test_directory")

        # Flatten nested lists and included 'sequence' entries to the same level
        # in one linear pass (was an in-place splice + full list rebuild per
        # entry: O(n^2) over the step list).
        flat_actions = []
        _flatten_actions(parent_seq_actions, flat_actions, parent_seq_name)

        for action in flat_actions:
            # After flattening, each step must be a single-key mapping
            # '{item_cmd: {params...}}'. Anything else is a structural mistake
            # in the .tum (a stray scalar, a missing '-' marker, an over- or
            # under-indented block) — report it with its location instead of
            # crashing on it below.
            if not isinstance(action, dict):
                raise ETUMSyntaxError(
                    f"In: {path}\n"
                    f"A step is not a valid test item: expected a "
                    f"'<item>: ...' mapping but got {type(action).__name__} "
                    f"({action!r}).\n"
                    f"Check the indentation and the '-' list markers of 'steps'.",
                    file_name
                )
            if len(action) != 1:
                raise ETUMSyntaxError(
                    f"In: {path}\n"
                    f"A step must define exactly one test item but defines "
                    f"{len(action)}: {sorted(map(str, action.keys()))}.\n"
                    f"Each '-' step holds a single '<item>:'; the lines below it "
                    f"are probably its parameters and need one more indent level.",
                    file_name
                )

            k = list(action.keys())[0]

            # The body of an item is its parameter mapping. A bare '<item>:'
            # (None) is tolerated as an empty parameter set; a scalar or list is
            # a structural mistake and is reported with its location.
            body = action[k]
            if body is None:
                body = {}
                action[k] = body
            if not isinstance(body, dict):
                raise ETUMSyntaxError(
                    f"In: {path}\n"
                    f"The body of test item '{k}' must be a mapping of "
                    f"parameters but is {type(body).__name__} ({body!r}).",
                    file_name
                )

            if body.get("seq_filename", None) is None:
                body["seq_filename"] = file_name
            seq_filename = body["seq_filename"]

            executed = False
            for it in TEST_TYPE_LIST:
                # Test items not executable
                if (
                    (it == cst_type.TYPE_ROOT)
                    or
                    # Items which don't have to be loaded by test_set module
                    (it.item_class is None)
                ):
                    continue
                if k not in (it.item_cmd, cst.FOLDED_CHAR + it.item_cmd):
                    continue
                executed = True
                # A "." before the cmd name means the item is folded in the GUI
                is_folded = k.startswith(cst.FOLDED_CHAR)
                try:
                    item = (it.item_class)(
                        body,
                        tree_parent,
                        self.status_queue,
                        filename=seq_filename
                    )
                    item.is_folded = is_folded
                    child = {}
                    # case where the test item loads itself its descendants
                    if it in (cst_type.TYPE_UNITTEST, cst_type.TYPE_PYTEST):
                        item.setTestDir(test_dir)
                        child = self._load_item(item)
                    elif issubclass(it.item_class, TestItemActions):
                        child = item.load()
                    # case where the test item is an items container
                    elif item.is_container:
                        child = self.load_test_recursively(
                            item, body, seq_filename
                        )
                except ETUMError as e:
                    # Any testium error raised while building the item gets the
                    # location prefix (unless a deeper level already added it).
                    msg = e._message
                    if not msg.lstrip().startswith("In:"):
                        msg = f"In: {path} > {k}\n{msg}"
                    raise type(e)(msg, e._file or seq_filename) from e
                except Exception as e:
                    # Anything unexpected: never let a raw Python error reach the
                    # user as 'crashed for any reason' — locate it precisely.
                    raise ETUMSyntaxError(
                        f"In: {path} > {k}\n"
                        f"Unexpected error while loading this item: "
                        f"{type(e).__name__}: {e}",
                        seq_filename
                    ) from e

                ret.update(test_data(item, child))

            if not executed:
                known = ", ".join(
                    t.item_cmd for t in TEST_TYPE_LIST
                    if t is not cst_type.TYPE_ROOT and t.item_class is not None
                )
                raise ETUMSyntaxError(
                    f"In: {path}\n"
                    f"'{k}' is not a known test item.\n"
                    f"Known items: {known}.",
                    seq_filename
                )

        return ret

    def tree(self):
        return self._tree

    def skipped_state(self):
        ret = {}
