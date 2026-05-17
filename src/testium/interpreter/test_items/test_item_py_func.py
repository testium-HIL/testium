import sys
import traceback
import time
import pprint
import textwrap

from runtime.tum_except import ETUMSyntaxError, ETUMRuntimeError, item_load_context
from interpreter.test_items.test_item import TestItem, test_run
from interpreter.test_items.test_result import TestValue
import api.testium as tm
from interpreter.utils.py_func_exec import PyFuncExecEngine
from interpreter.utils.api_srv import api_request
from interpreter.utils.constants import TestItemType as cst

_PY_FUNC_CONTEXTS_KEY = "_py_func_contexts"


class TestItemPyFunc(TestItem):
    """py_func item usage.
    func file: func_file.py, func_name: func, param: [$(variable1), [1, 2, 3], true]
    Optional: context_id: <id>  — share a persistent process with other py_func items using the same id.
    """

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_PY_FUNCTION.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_PY_FUNCTION
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self.file_name = self._prms.getParam("file", required=True)
            self.func_name = self._prms.getParam("func_name", required=True)
            self.params = self._prms.getParamAll("param")
            self._context_id = self._prms.getParam("context_id", default=None, processed=False)
        self._py_func_proc = PyFuncExecEngine(api_request, 10)

    def _get_engine(self):
        """Return (engine, persistent). If context_id is set, use a shared persistent engine."""
        if self._context_id is None:
            return self._py_func_proc, False

        ctx_id = self._prms.expanse(self._context_id)
        contexts = tm.gd(_PY_FUNC_CONTEXTS_KEY, {})
        if ctx_id not in contexts:
            contexts[ctx_id] = PyFuncExecEngine(api_request, 10)
            tm.setgd(_PY_FUNC_CONTEXTS_KEY, contexts)
        return contexts[ctx_id], True

    def stop(self):
        super().stop()
        # Tear down the worker so any in-flight func_call returns promptly.
        # join() clears _rpc/_process so a subsequent item reusing the same
        # context_id can restart the engine cleanly.
        try:
            engine, _ = self._get_engine()
            engine.stop()
            engine.join()
        except Exception:
            pass

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
            print("Parameters list:")
            print(textwrap.indent(pprint.pformat(pl), " |"))

            engine, persistent = self._get_engine()

            if not engine.is_alive():
                engine.start()
                if not engine.wait_ready():
                    raise ETUMRuntimeError(
                        f"""Impossible to start the external python execution process.
Is the python path correct ?
python_bin = {tm.gd("python_bin", "no python path defined")}"""
                    )

            try:
                success, ret = engine.func_call(self.file_name, self.func_name, pl)
            finally:
                if not persistent:
                    engine.stop()
                    engine.join()

            if success == TestValue.SUCCESS:
                self.result.set(TestValue.SUCCESS)
                res, reported_values = ret
                reported_values = {**reported_values, "returned": res}
                self.result.reported = ret[1]
                print("Returned value:")
                print(textwrap.indent(pprint.pformat(res), " |"))

                tm.setgd("pfn_" + self._name, res)
                self.result.value = res

            else:
                self.result.set(TestValue.FAILURE, ret)
                print("Failed!")
                tm.print_debug(textwrap.indent(pprint.pformat(ret), " |"))

            return

        except ConnectionAbortedError:
            self.result.set(TestValue.FAILURE, "py_func aborted on stop request")
            print("py_func aborted on stop request.")
        except:
            traceback.print_exception(*sys.exc_info())
            if self.isStopped():
                self.result.set(TestValue.FAILURE, "py_func aborted on stop request")
            else:
                self.result.set(
                    TestValue.FAILURE,
                    'Unrecoverable "py_func" item error from {}'.format(self.func_name),
                )
