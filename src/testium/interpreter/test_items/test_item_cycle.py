import traceback

from runtime.tum_except import ETUMSyntaxError, ETUMRuntimeError
from interpreter.utils.py_func_exec import PyFuncExecEngine
from interpreter.utils.api_srv import api_request
from interpreter.test_items.test_item import TestItem, test_run
from interpreter.test_items.test_result import TestResult, TestValue
import api.testium as tm
from interpreter.utils.params import TestItemParams
from interpreter.utils.constants import TestItemType as cst


class TestItemCycle(TestItem):
    def __init__(self, dict_cycle, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_CYCLE.item_name
        super().__init__(dict_cycle, parent, status_queue, filename=filename)
        self._type = cst.TYPE_CYCLE
        self.is_container = True
        self._exit_file = None
        self._exit_func = None
        self._exit_time = None
        self._exit_condition = None
        self._start_time = None
        self._niter = None

        if "iterator" in dict_cycle:
            self._iter = dict_cycle["iterator"]

            if isinstance(self._iter, str):
                self._iter = self._prms.expanse(self._iter)

        else:
            self._iter = None

        if "exit_condition" in dict_cycle:
            if not isinstance(dict_cycle["exit_condition"], dict):
                raise ETUMSyntaxError(
                    f"The '{self.cmd()}' test item named '{self.name()}' has an error in its exit condition",
                self.seqFilename()
            )

            exit_params = TestItemParams(dict_cycle["exit_condition"], self._parent)
            self._exit_time = exit_params.getParam("time", processed=False)
            self._exit_condition = exit_params.getParam("value", processed=False)

            req = False
            if (self._exit_time is None) and (self._exit_condition is None):
                req = True

            self._exit_file = exit_params.getParam("file", required=req)
            self._exit_func = exit_params.getParam("func_name", required=req)
            self._exit_func_param = exit_params.getParam("param")
            self._exit_eval = exit_params.getParam("eval", default="")

    def __runALoop(self):
        failcount = 0
        i = 0
        to_be_stopped = False
        while (
            (not self.isStopped()) and (i < self.childCount()) and (not to_be_stopped)
        ):
            result = self.child(i).execute()
            if result.test_result == TestValue.FAILURE:
                failcount = failcount + 1
                if self._stop_on_failure:
                    to_be_stopped = True
            i = i + 1

        if self.isStopped() or to_be_stopped:
            for j in range(self.childCount()):
                if self.child(j).executedOnStop() and (j >= i):
                    self.child(j).execute()

        test_success = TestValue.SUCCESS
        if failcount > 0:
            test_success = TestValue.FAILURE

        result = TestResult(None, test_success, "Cycle iteration")
        return result

    def nbLoops(self, iter):
        if iter is None:
            # infinite number of loop
            self._niter = float("inf")
        elif isinstance(iter, int):
            self._niter = iter
        else:
            self._niter = len(iter)
        return self._niter

    @test_run
    def execute(self):
        failcount = 0
        iter = self._iter
        if iter is not None:
            if isinstance(iter, str):
                iter = self._prms.expanse(iter)

            if not isinstance(iter, (list, tuple, int)):
                self.result.set(TestValue.FAILURE, f"unrecognized type for iterator '{str(iter)}'")
                return

            if not isinstance(iter, int):
                r = []
                for i in iter:
                    r.append(self._prms.expanse(i))
                iter = r


        # test core function
        self._niter = self.nbLoops(iter)
        i = 1
        to_be_stopped = False
        self._start_time = tm.timestamp_as_sec()
        self.result.set(TestValue.SUCCESS, "Initial cycle setup")
        while (i <= self._niter) and (not self.isStopped()) and (not to_be_stopped):
            try:
                msg = ""
                if isinstance(iter, int) or iter is None:
                    msg = "{}/{}".format(i, self._niter)
                    self.sendMessage("Cycle " + msg)
                    msg = 'Cycle "' + self._name + '" iteration ' + msg + "."
                else:
                    msg = '{}/{} - Current: "{}"'.format(i, self._niter, str(iter[i - 1]))
                    self.sendMessage("Cycle " + msg)
                    msg = 'Cycle "' + self._name + '" iteration ' + msg + "."
                print(msg)

                # store the current loop params
                self._currentIter = i - 1
                self._currentInverseIter = self._niter - i - 1
                if isinstance(iter, int) or iter is None:
                    self._currentLoop = i
                else:
                    self._currentLoop = iter[i - 1]
                # Cycle loop execution
                res_loop = self.__runALoop()

                if not res_loop.success:
                    failcount = failcount + 1
                    self.result.set(
                        TestValue.FAILURE, "(Cycle {}/{})".format(i - 1, self._niter)
                    )
                # Cycle time exit condition check
                if res_loop.success or (
                    (not res_loop.success) and (not self._stop_on_failure)
                ):
                    if self._exit_time is not None:
                        ela = tm.timestamp_as_sec()
                        etime = self._prms.expanse(self._exit_time)
                        if (ela - self._start_time) > float(etime) * 60:
                            self.result.reported = {
                                "exit": "time elapsed",
                                "timeout": etime,
                                "elapsed": (ela - self._start_time) / 60,
                                "count": self._currentIter,
                            }
                            print(
                                "Exiting loop: {:.1f} minutes elapsed (defined: {}).".format(
                                    (ela - self._start_time) / 60, etime
                                )
                            )
                            break
                        else:
                            print(
                                "loop: {:.1f} minutes elapsed (exiting when > {}).".format(
                                    (ela - self._start_time) / 60, etime
                                )
                            )

                    # Cycle value exit condition check
                    if self._exit_condition is not None:
                        exit_val = self._prms.expanse(
                            self._exit_condition
                        )
                        ev = False
                        if isinstance(exit_val, bool):
                            ev = exit_val
                        else:
                            tm.print_warn(f"""Loop 'exit_condition' is not a boolean value ({exit_val}),
then considered as 'False'""")
                        if ev:
                            # exit condition is True
                            self.result.reported = {
                                "exit": "condition",
                                "condition": self._exit_condition,
                                "count": self._currentIter,
                            }
                            print(
                                'Exiting loop: "{}" is True.'.format(
                                    self._exit_condition
                                )
                            )
                            break
                        else:
                            print(
                                f"Continuing. Condition '{self._exit_condition}' not a 'True' boolean."
                            )

                    if self._exit_func:
                        file = self._prms.expanse(self._exit_file)
                        func = self._prms.expanse(self._exit_func)
                        post_eval = self._prms.expanse(self._exit_eval)
                        if self._exit_func_param:
                            param_list = self._prms.getParamFromList(self._exit_func_param)
                            pl = self._prms.expanse(param_list)
                        else:
                            pl = [self._currentLoop]

                        proc = PyFuncExecEngine(api_request, 10)
                        proc.start()
                        if not proc.wait_ready(10):
                            raise ETUMRuntimeError(
                                f"""Impossible to start the external python execution process.
Is the python path correct ?
python_bin = {tm.gd("python_bin", "no python path defined")}"""
                            )
                        try:
                            fsucc, res = proc.func_call(file, func, pl)
                        finally:
                            proc.stop()
                            proc.join()

                        if fsucc == TestValue.SUCCESS:
                            fres, _ = res
                            if fres:
                                # function returned True
                                self.result.reported = {
                                    "exit": "returned value",
                                    "returned": fres,
                                    "count": self._currentIter,
                                }
                                print("Exiting loop: exit function condition met.")
                                break
                            else:
                                print("Exiting condition not met : \"{}\"".format(fres))
                        else:
                            raise ETUMRuntimeError(f"Loop exiting function failed: \"{res}\"")

                        if post_eval:
                            print(f"Evaluation: \"{post_eval}\"")

            except:
                print(traceback.format_exc())
                self.result.set(TestValue.FAILURE, "(Cycle {}/{})".format(i - 1, self._niter))
                to_be_stopped = True

            if (self.result.test_result == TestValue.FAILURE) and self._stop_on_failure:
                to_be_stopped = True
            i = i + 1

        # end of loop test exit condition
        if self.isStopped() or to_be_stopped:
            if to_be_stopped:
                self.result.set(
                    TestValue.FAILURE,
                    "(Cycle {}/{}) execution aborted on failure".format(i - 1, self._niter),
                )
            else:
                if self._exit_func:
                    self.result.set(
                        TestValue.FAILURE,
                        "(Cycle {}/{}) execution aborted on user request".format(
                            i - 1, self._niter
                        ),
                    )
                else:
                    self.result.set(
                        TestValue.SUCCESS, "(Cycle {}/{})".format(self._niter, self._niter)
                    )
                    if failcount > 0:
                        self.result.set(
                            TestValue.FAILURE, "(Cycle {}/{})".format(i - 1, self._niter)
                        )

        else:
            self.result.set(TestValue.SUCCESS, "(Cycle {}/{})".format(self._niter, self._niter))
            if failcount > 0:
                self.result.set(TestValue.FAILURE, "(Cycle {}/{})".format(i - 1, self._niter))
