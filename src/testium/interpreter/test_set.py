import os
import datetime
from queue import Queue
from interpreter.utils.params import expanse
import libs.testium as tm
from lib.tum_except import (
    ETUMSyntaxError,
)
import interpreter.utils.settings as prefs
from interpreter.test_report.test_report import TestReport
from interpreter.utils.py_func_exec import PyFuncExecEngine
from interpreter.utils.api_srv import api_request
from lib.tum_except import ETUMRuntimeError
from interpreter.utils.constants import TestItemType as cst_type
import interpreter.utils.constants as cst
from interpreter.utils.constants import TEST_TYPE_LIST
from interpreter.test_items.test_item import test_data
from interpreter.test_items.item_actions import TestItemActions
from interpreter.test_items.test_result import TestValue


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

        self._tree = self.__loadTestTree(tum_fime)
        self.dict_report = self._testdict.get("report", None)
        self.set_post_exec()

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
            a_test_is_skipped = self.__aTestIsSkipped(self._rootItem)
            a_test_is_disabled = self.__aTestIsDisabled(self._rootItem)
            res = self._rootItem.execute()
        finally:
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
        self._rootItem.stop()
        self.__stopRunningTestsRecursively(self._rootItem)

    def __pauseTestsRecursively(self, parent):
        for i in range(parent.childCount()):
            if parent.child(i).isRunning():
                parent.child(i).pause()
            self.__pauseTestsRecursively(parent.child(i))

    def pause(self):
        self._rootItem.pause()
        self.__pauseTestsRecursively(self._rootItem)

    def __setReportRecursively(self, parent):
        for i in range(parent.childCount()):
            parent.child(i).report = self._report
            self.__setReportRecursively(parent.child(i))

    def setReport(self):
        self._rootItem.report = self._report
        self.__setReportRecursively(self._rootItem)

    def addBreakpoint(self, item_id):
        item = self.__findItemById(item_id)
        item.addBreakpoint()

    def delBreakpoint(self, item_id):
        item = self.__findItemById(item_id)
        item.delBreakpoint()

    def __continueTestsRecursively(self, parent):
        for i in range(parent.childCount()):
            if parent.child(i).isRunning():
                parent.child(i).cont()
            self.__continueTestsRecursively(parent.child(i))

    def cont(self):
        self._rootItem.cont()
        self.__continueTestsRecursively(self._rootItem)

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
        ret = self.load_test_recursively(self._rootItem, dict_main, filename)
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

        proc = PyFuncExecEngine(tm.gd("python_bin", ""), api_request, 10)
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
                    tm.print_debug(
                        f"Test success but the \"post_exec\" function failed: {res}"
                    )
            else:
                succ, res = proc.func_call(post_exec_file, "post_exec_fail", [])
                if not succ == TestValue.SUCCESS:
                    tm.print_debug(
                        f"Test failed but the \"post_exec_fail\" function failed: {res}"
                    )
        finally:
            proc.stop()
            proc.join()

    def rootItem(self):
        return self._rootItem

    def load_test_recursively(self, tree_parent, parent_seq, file_name):
        ret = {}
        try:
            parent_seq_name = parent_seq["name"]
        except KeyError:
            parent_seq["name"] = "sequence"
        except TypeError:
            raise ETUMSyntaxError(
                f"No 'name' attribute in '{tree_parent.type()}' (a child of '{tree_parent.parent().name()}')",
                file_name
            )
        try:
            parent_seq_actions = parent_seq["steps"]
        except KeyError:
            raise ETUMSyntaxError(
                f"No step list found for '{parent_seq_name}' sequence. \n" +
                f"Check the syntax of the 'steps' parameter of the '{tree_parent.cmd()}' test item definition.",
                file_name
            )
        # if action is a dictionary , we assume it is a single action
        # that has not been nested in a list, so do it
        if isinstance(parent_seq_actions, (dict)):
            parent_seq_actions = [parent_seq_actions]
        if not isinstance(parent_seq_actions, (list, tuple)):
            raise ETUMSyntaxError(
                f"No valid list of actions in sequence {parent_seq_name}",
                file_name
            )
        # first we merged to the same level 'sequence dict entries and list within the list
        counter = 0
        test_dir = tm.gd("test_directory")
        la = len(parent_seq_actions)
        while counter < la:
            action = parent_seq_actions[counter]
            # if action is a list raise up to the the same level,
            # ie insert action element into the parent_seq_actions
            if isinstance(action, (list, tuple)):
                parent_seq_actions[counter : counter + 1] = action
                parent_seq_actions = (
                    parent_seq_actions[:counter]
                    + action
                    + parent_seq_actions[counter + 1 :]
                )
                la = len(parent_seq_actions)
                continue
            # if action is a NoneType skip and continue
            # (when pointing to an unused alias for instance)
            if action is None:
                counter += 1
                continue
            # if action is a sequence we insert its entry into the action list
            if "sequence" in action:
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
                        f"Syntax error in '{parent_seq_name}' step number {counter+1}. Sequence definition: '{str(action)}'",
                        f
                    )
                for s in sequence:
                    s[list(s.keys())[0]]["seq_filename"] = f
                parent_seq_actions = (
                    parent_seq_actions[:counter]
                    + sequence
                    + parent_seq_actions[counter + 1 :]
                )
                la = len(parent_seq_actions)
                continue

            # Action is now for sure a list of dict of length 1
            k = list(action.keys())[0]
            if action[k].get("seq_filename", None) is None:
                action[k]["seq_filename"] = file_name

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
                if (it.item_cmd in action) or (
                    (cst.FOLDED_CHAR + it.item_cmd) in action
                ):
                    executed = True
                    is_folded = False
                    action_name = it.item_cmd

                    # Check if a "." is before the cmd_name (meaning folded)
                    if (cst.FOLDED_CHAR + it.item_cmd) in action:
                        is_folded = True
                        action_name = cst.FOLDED_CHAR + it.item_cmd

                    seq_filename = action[action_name]["seq_filename"]
                    item = (it.item_class)(
                        action[action_name],
                        tree_parent,
                        self.status_queue,
                        filename=seq_filename
                    )
                    item.is_folded = is_folded
                    child = {}
                    # case where the test item loads itself its descendants
                    if it == cst_type.TYPE_UNITTEST_FILE:
                        item.setTestDir(test_dir)
                        child = item.load()
                    elif issubclass(it.item_class, TestItemActions):
                        child = item.load()
                    # case where the test item is an items container
                    elif item.is_container:
                        child = self.load_test_recursively(
                            item, action[action_name], seq_filename
                        )

                    ret.update(test_data(item, child))

            if not executed:
                raise ETUMSyntaxError(
                    f"test item '{k}' is not known.",
                    action[k]["seq_filename"]
                )

            counter += 1

        return ret

    def tree(self):
        return self._tree

    def skipped_state(self):
        ret = {}
