from functools import wraps
from time import sleep
import yaml
from copy import deepcopy
from interpreter.test_items.test_result import TestResult, TestValue
import libs.testium as tm
from interpreter.utils.params import TestItemParams
from interpreter.utils.constants import TestItemType as cst_type
from interpreter.utils.eval import eval_to_boolean, evaluate, post_evaluate
from interpreter.utils.tum_except import ETUMSyntaxError

LOG_TEST_STOP = '<----- step "{}" finished'
LOG_TEST_START = '-----> step "{}" started'


class TestItem:
    pass


def test_run(f):
    @wraps(f)
    def wrapper(self):
        if not self.skipped:
            if self.enabled:
                self.run_test_init()
                # Conditional execution
                raw_condition = self._prms.getParam(
                    "condition", default=None, processed=False
                )
                if raw_condition is None:
                    condition = True
                else:
                    c = self._prms.expanse(raw_condition)
                    if isinstance(c, bool):
                        condition = c
                    elif isinstance(c, (str, bytes)):
                        is_evaluated, condition = evaluate(c)
                        if not is_evaluated:
                            print("eval with c: {}".format(c))
                            raise ETUMSyntaxError(
                                f"The '{self.cmd()}' test item named '{self.name()}' has a 'condition' impossible to evaluate",
                                self.seqFilename(),
                            )
                    else:
                        raise ETUMSyntaxError(
                            f"The '{self.cmd()}' test item named '{self.name()}' has a 'condition' result ({c}) which is not string or bool",
                            self.seqFilename(),
                        )

                    msg = '"{}" --> "{}"'.format(raw_condition, c)

                # Do we have to skip the test because of a true condition ?
                if condition:
                    if not raw_condition is None:
                        msg = "condition met: " + msg
                        self.result.reported = {"input_condition": msg}
                        print(msg)
                    # Test preparation
                    self.run_before_test()
                    # Test execution
                    f(self)
                else:
                    msg = "condition not met: " + msg
                    self.result.set(TestValue.NORUN, msg)
                    self.result.reported = {"input_condition": msg}
                self.run_test_end()
            else:
                self.result.set(TestValue.NORUN, "test disabled")
                print("Test is disabled.")
        else:
            self.result.set(TestValue.NORUN, "test skipped")
            print("Test is skipped.")

        return self.result

    return wrapper


def test_data(item: TestItem, child: dict) -> dict:
    return {
        item.id(): {
            "id": item.id(),
            "name": item.name(),
            "type": item.type(),
            "doc": None if (item.doc() == "") or (item.doc() == None) else item.doc(),
            "content": item.content(),
            "folded": item.is_folded,
            "seq_filename": item.seqFilename(),
            "child": child,
        }
    }


class TestItem:
    def __init__(
        self, dict_item: dict = None, parent: TestItem = None, status_queue=None, filename = ""
    ):
        self.enabled = True
        self.skipped = False
        self.is_container = True
        self.is_folded = False
        self._children = []
        self._parent = parent
        self._id = id(self)
        self._type = cst_type.TYPE_ROOT
        self._report_key = None
        self._reported = None
        self.status_queue = status_queue
        self._execute_on_stop = False
        self._post_eval = None
        self._expected_result = None
        self._no_fail = None
        self._is_stopped = False
        self._is_running = False
        self._is_breakpoint = False
        self._is_paused = False
        self._stop_on_failure = False
        self._doc = ""
        self._name = ""
        self.report = None
        self._dict_item = self._filter_dict_item(dict_item)
        self._seq_filename = filename

        if parent is not None:
            parent.addChild(self)

        if dict_item is not None:
            # creation of the params object
            self._prms = TestItemParams(dict_item, parent)

            # getting parameters for the test item
            try:
                self._name = self._prms.getParam("name", default="", processed=True)
                # robustness if "name:" followed by an empty string in the yaml.
                if self._name == None:
                    self._name = ""
                s = self._prms.getParam("skipped", default=None, processed=True)
                if s:
                    try:
                        self.skipped = eval_to_boolean(s)
                    except:
                        raise ETUMSyntaxError(
                            f"'{self.cmd()}' test item named '{self.name()}':\nskipped expresion can only be a static expression as it is evaluated during loading of TUM : {s}",
                            self.seqFilename(),
                        )
                # This allow disabling test item directly by using its name inside param.yaml file
                elif self._name in tm.gd("skipped_test_item", []):
                    self.skipped = True
                else:
                    self.skipped = False

                self._report_key = self._prms.getParam("key", default=None)
                self._stop_on_failure = self._prms.getParam(
                    "stop_on_failure", default=False, processed=True
                )
                self._doc = self._prms.getParam("doc", default="", processed=True)
                #
                self._execute_on_stop = self._prms.getParam(
                    "execute_on_stop", default=False, processed=True
                )

                if "process_result" in dict_item:
                    self._post_eval = dict_item["process_result"]

                if "expected_result" in dict_item:
                    self._expected_result = dict_item["expected_result"]

                if "no_fail" in dict_item:
                    self._no_fail = dict_item["no_fail"]

                self.banner = LOG_TEST_START.format(self._name)
                self.footer = LOG_TEST_STOP.format(self._name)

            except:
                raise ETUMSyntaxError(
                    f"The '{self.cmd()}' test item named '{self.name()}' has a missing or wrong parameter",
                    self.seqFilename(),
                )

        self.result = TestResult(self, TestValue.FAILURE, "Failure by default")

    def _filter_dict_item(self, dict_item):
        # Stores the content of the step to be displayed
        # in the GUI
        c = {}
        if isinstance(dict_item, dict):
            for k, v in dict_item.items():
                if k == "steps" or k == "name" or k == "doc" or k == "seq_filename":
                    continue
                if isinstance(v, (list, dict)):
                    val = deepcopy(v)
                else:
                    val = v
                c.update({k: val})
        else:
            c = str(dict_item)

        return c

    # default behavior... must be overloaded by children
    # this is mostly used by root item
    @test_run
    def execute(self):
        test_results = []
        i = 0
        to_be_stopped = False
        while (not self.isStopped()) and (i < self.childCount()) and not to_be_stopped:
            test_res = self.child(i).execute()
            test_results.append(test_res)
            i = i + 1
            if test_res.test_result == TestValue.FAILURE and self._stop_on_failure:
                to_be_stopped = True
        if self.isStopped() or to_be_stopped:
            for j in range(self.childCount()):
                if self.child(j).executedOnStop() and (j >= i):
                    self.child(j).execute()
            if to_be_stopped:
                self.result.set(TestValue.FAILURE, "test stopped on failure")
            else:
                test_success = TestValue.SUCCESS
                for res in test_results:
                    if res.test_result != TestValue.SUCCESS:
                        test_success = TestValue.FAILURE
                        break
                self.result.test_result = test_success
        else:
            test_success = TestValue.SUCCESS
            for res in test_results:
                if res.test_result != TestValue.SUCCESS:
                    test_success = TestValue.FAILURE
                    break
            self.result.test_result = test_success
            self.result.message = "Test run failed"

    def write_banner(self):
        if self.parent() is not None:
            s = self.banner
            s = (s + "{:>" + str(max(1, 80 - len(s))) + "}").format(
                str("@@{}@@".format(self.t0))
            )
            print(s)

    def write_footer(self):
        if self.parent() is not None:
            print(self.result.message)
            print(self.footer + f": {str(self.result.test_result)}")

    def run_test_init(self):
        """Common test items execution initialization."""
        self.t0 = tm.timestamp()
        if self._name != "":
            tm.setgd("ts_start_" + self._name, self.t0)
        self.duration = -1
        self.write_banner()
        self._is_running = True
        self._sendStatusStarted()
        if self._is_breakpoint:
            self._is_paused = True
            while self._is_paused:
                sleep(0.2)

        if self.is_container:
            self.report.incLevel()

        self._reported = self._prms.getParam("report", default=None, processed=False)

    def run_before_test(self):
        """Peace of code executed just before the test is
        executed.
        """
        pass

    def run_test_end(self):
        """Common test items execution closure."""
        if self.is_container:
            self.report.decLevel()

        while self._is_paused:
            sleep(0.2)

        # Post evaluation of the test result
        self.process_result()
        # expected_result treatment
        self.result_expected()
        # Case of the no_fail true parameter
        self.process_no_fail()

        self.result.sendStatus(self.status_queue)
        if not self.result.value is None:
            tm.setgd("last_test_result", str(self.result.value))
        else:
            tm.setgd("last_test_result", str(self.result.test_result))
        self.write_footer()
        self._is_running = False
        self._is_stopped = False
        self.t1 = tm.timestamp()
        self.duration = self.t1 - self.t0
        if self._name != "":
            tm.setgd("ts_end_" + self._name, self.t1)
            tm.setgd("ts_duration_" + self._name, tm.timestamp_as_sec(self.duration))
        rk = self._prms.expanse(self._report_key)

        # Report value export
        if hasattr(self.report, "value") and self.report.value is not None:
            self.result.reported = {"result": self.report.value}

        if not self._reported is None:
            self.process_report(self._reported)
        self.report.addTest(self, self.result, rk)
        self._sendStatusFinished()

    def process_result(self):
        if self._post_eval is None:
            return
        print(f"Post-processed the test result:")
        r = self.result.value
        pe = self._prms.expanse(self._post_eval)
        try:
            self.result.value = self.post_evaluate(pe)
            print(f"   was: {r}")
            print(f"   is:  {str(self.result.value)}")
        except Exception as e:
            print("   Result processing failed!")
            print(e)
            self.result.set(TestValue.FAILURE, "Result processing failed")

        if isinstance(self.result.value, bool):
            if self.result.value:
                self.result.set(TestValue.SUCCESS, "Processing result returned 'True'")
            else:
                self.result.set(TestValue.FAILURE, "Processing result returned 'False'")

    def process_report(self, report_eval):
        tm.print_debug(f"Export reported values:")
        rep_eval = self._prms.expanse(report_eval)
        if isinstance(rep_eval, dict):
            self.result.reported = rep_eval
            if tm.debug_enabled():
                for k, v in rep_eval.items():
                    tm.print_debug(f"   {k}: {v}")
        else:
            tm.print_debug("   Failed: the reported value must be a dictionnary.")

    def result_expected(self):
        res = self.result.value

        # if a result is expected
        e = None
        eres = None

        if not self._expected_result is None:
            e = self._prms.expanse(self._expected_result)
            _, eres = evaluate(e)

        if not eres is None:
            if not res is None:
                print("Compare the result to expected:")
                print("   Result   = " + str(res))
                msg = "   Expected = " + str(self._expected_result)
                if self._expected_result != eres:
                    msg = msg + " -> " + str(eres)
                print(msg)
                self.result.reported = {"expected": eres}

                if eres == res:
                    self.result.set(TestValue.SUCCESS, f"Expected result met.")
                else:
                    self.result.set(TestValue.FAILURE, f"Expected result not met.")
            else:
                if str(eres).lower() != str(self.result.test_result).lower():
                    self.result.set(
                        TestValue.FAILURE, "Expected result not met : {}.".format(e)
                    )
                else:
                    self.result.set(
                        TestValue.SUCCESS, "Expected result met: {}.".format(e)
                    )

    def process_no_fail(self):
        # Treatment of the no_fail parameters
        if self._no_fail is None:
            return

        no_fail = False
        no_fail_exp = self._prms.expanse(self._no_fail)
        try:
            no_fail = bool(no_fail_exp)
        except:
            tm.print_debug(
                f"The 'no_fail' parameter evaluation did not lead to a boolean value: '{no_fail}'"
            )
            tm.print_warn(
                "The 'no_fail' parameter is ignored due to evaluation error."
            )
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' has a 'no_fail' parameter impossible to evaluate",
                self.seqFilename(),
            )
        if no_fail:
            if self.result.test_result == TestValue.FAILURE:
                tm.print_info(f"'no_fail' is True. Test forced to PASS.")
                self.result.test_result = TestValue.SUCCESS

    def post_evaluate(self, post_eval):
        res = self.result.value
        if self.result.value is None:
            res = self.result.test_result
        return post_evaluate(post_eval, res)

    def doc(self) -> str:
        return self._doc

    def _sendStatusStarted(self):
        status = {
            "id": self._id,
            "name": self._name,
            "status": "started",
            "timestamp": self.t0,
        }
        self.status_queue.put(status)

    def _sendStatusFinished(self):
        status = {
            "id": self._id,
            "name": self._name,
            "status": "finished",
            "duration": self.duration,
        }
        self.status_queue.put(status)

    def sendMessage(self, msg):
        status = {"id": self._id, "name": self._name, "message": msg}
        self.status_queue.put(status)

    def isRunning(self):
        return self._is_running

    def isStopped(self):
        return self._is_stopped

    def stop(self):
        self._is_stopped = True

    def pause(self):
        self._is_paused = True

    def addBreakpoint(self):
        self._is_breakpoint = True

    def delBreakpoint(self):
        self._is_breakpoint = False

    def cont(self):
        self._is_paused = False

    def name(self):
        return self._name

    def content(self):
        ret = (
            yaml.dump(
                {self.cmd(): self._dict_item}, allow_unicode=True, sort_keys=False
            )
            if len(self._dict_item) != 0
            else ""
        )
        return ret

    def type(self):
        return self._type.item_name

    def cmd(self):
        return self._type.item_cmd

    def childCount(self):
        return len(self._children)

    def setId(self, id):
        self._id = id

    def id(self):
        return self._id

    def setEnabled(self):
        self.enabled = True

    def executedOnStop(self):
        return self._execute_on_stop

    def addChild(self, child):
        self._children.append(child)

    def hasChildren(self):
        return self.childCount() > 0

    def parent(self):
        return self._parent

    def child(self, index):
        return self._children[index]

    def load(self):
        pass

    def setSeqFilename(self, filename):
        self._seq_filename = filename

    def seqFilename(self):
        return self._seq_filename
