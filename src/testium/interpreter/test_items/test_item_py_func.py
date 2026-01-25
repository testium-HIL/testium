import sys
import traceback

import pprint
import textwrap

from interpreter.test_items.test_item import TestItem, test_run
from interpreter.test_items.test_result import TestValue
import libs.testium as tm
from interpreter.utils.py_func_exec import PyFuncExecEngine
from interpreter.utils.api_srv import api_request
from interpreter.utils.tum_except import ETUMSyntaxError, ETUMRuntimeError
from interpreter.utils.constants import TestItemType as cst


class TestItemPyFunc(TestItem):
    """py_func item usage.
    func file: func_file.py, func_name: func, param: [$(variable1), [1, 2, 3], true]
    """

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_PY_FUNCTION.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_PY_FUNCTION
        self.is_container = False
        try:
            self.file_name = self._prms.getParam("file", required=True)
            self.func_name = self._prms.getParam("func_name", required=True)
            self.params = self._prms.getParamAll("param")
        except:
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' (child of '{self.parent.name()}') has a missing or wrong parameter",
                self.seqFilename(),
            )
        self._proc = PyFuncExecEngine(tm.gd("python_bin", ""), api_request, 10)

    @test_run
    def execute(self):
        self.result.set(
            TestValue.FAILURE, "an exception occured during function execution."
        )
        try:
            self.file_name = self._prms.expanse(self.file_name)
            self.func_name = self._prms.expanse(self.func_name)
            param_list = self._prms.getParamFromList(self.params)
            pl = self._prms.expanse(param_list)
            if tm.debug_enabled():
                tm.print_debug("Parameters list:")
                tm.print_debug(textwrap.indent(pprint.pformat(pl), " |"))

                # start the process for executing external python
                self._proc.start()
                if not self._proc.wait_ready(10):
                    raise ETUMRuntimeError(
                        f"""Impossible to start the external python execution process.
Is the python path correct ?
python_bin = {tm.gd("python_bin", "no python path defined")}"""
                    )

            try:
                success, ret = self._proc.func_call(self.file_name, self.func_name, pl)
            finally:
                # Stops python function execution process
                self._proc.stop()
                self._proc.join()

            if success == TestValue.SUCCESS:
                self.result.set(TestValue.SUCCESS)
                res, reported_values = ret
                reported_values = {**reported_values, "returned": res}
                self.result.reported = ret[1]

                if tm.debug_enabled():
                    tm.print_debug("Returned value:")
                    tm.print_debug(textwrap.indent(pprint.pformat(res), " |"))

                # The result of the func test item is put in global dir and result
                tm.setgd("pfn_" + self._name, res)
                self.result.value = res

            else:
                self.result.set(TestValue.FAILURE, ret)
                if tm.debug_enabled():
                    tm.print_debug("Failed:")
                    tm.print_debug(textwrap.indent(pprint.pformat(ret), " |"))

            return

        except:
            traceback.print_exception(*sys.exc_info())
            self.result.set(
                TestValue.FAILURE,
                'Unrecoverable "py_func" item error from {}'.format(self.func_name),
            )
