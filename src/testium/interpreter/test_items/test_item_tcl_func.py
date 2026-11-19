# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur

import sys
import traceback

import pprint
import textwrap

from runtime.tum_except import ETUMSyntaxError, ETUMRuntimeError, item_load_context
from interpreter.test_items.test_item import TestItem, test_run
from interpreter.test_items.test_result import TestValue
import api.testium as tm
from interpreter.utils.tcl_func_exec import TclFuncExecEngine
from interpreter.utils.api_srv import api_request
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.param_decl import Param, ParamSet, LIST

_TCL_FUNC_CONTEXTS_KEY = "_tcl_func_contexts"


class TestItemTclFunc(TestItem):
    """tcl_func item usage.
    func file: func_file.tcl, func_name: func, param: [$(variable1), [1, 2, 3], true]
    Optional: context_id: <id>: share a persistent process with other tcl_func items using the same id.
    """

    PARAMS = ParamSet(
        Param("file", required=True,
              doc="Path to the .tcl file containing the function."),
        Param("func_name", required=True,
              doc="Name of the proc to call, namespace allowed."),
        Param("param", kind=LIST,
              doc="Arguments passed to the function. Each entry is expanded "
                  "before the call. Special tokens $(loop_param) / $(loop_index) "
                  "resolve from the surrounding cycle."),
        Param("context_id", default=None,
              doc="If set, the tcl_func subprocess is kept alive and reused by "
                  "every other tcl_func item with the same context_id. Global "
                  "Tcl variables are then shared between successive calls."),
    )

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_TCL_FUNCTION.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_TCL_FUNCTION
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self.file_name = self._prms.getParam("file", required=True)
            self.func_name = self._prms.getParam("func_name", required=True)
            self.params = self._prms.getParamAll("param")
            self._context_id = self._prms.getParam("context_id", default=None, processed=False)
        self._tcl_func_proc = TclFuncExecEngine(api_request, 10)

    def _get_engine(self):
        """Return (engine, persistent). If context_id is set, use a shared persistent engine."""
        if self._context_id is None:
            return self._tcl_func_proc, False

        ctx_id = self._prms.expanse(self._context_id)
        contexts = tm.gd(_TCL_FUNC_CONTEXTS_KEY, {})
        if ctx_id not in contexts:
            contexts[ctx_id] = TclFuncExecEngine(api_request, 10)
            tm.setgd(_TCL_FUNC_CONTEXTS_KEY, contexts)
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
            # Locals: the raw templates must survive re-executions.
            file_name = self._prms.expanse(self.file_name)
            func_name = self._prms.expanse(self.func_name)
            param_list = self._prms.getParamFromList(self.params)
            pl = self._prms.expanse(param_list)
            print("Parameters list:")
            print(textwrap.indent(pprint.pformat(pl), " |"))

            engine, persistent = self._get_engine()

            if not engine.is_alive():
                engine.start()
                if not engine.wait_ready(10):
                    raise ETUMRuntimeError(
                        f"""Impossible to start the external tcl execution process.
Is the tclsh path correct ?
tcl_bin = {tm.gd("tcl_bin", "no tclsh path defined")}
Tcl 8.6 or later is required."""
                    )

            try:
                success, ret = engine.func_call(file_name, func_name, pl)
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

                tm.setgd("tfn_" + self._name, res)
                self.result.value = res

            else:
                self.result.set(TestValue.FAILURE, ret)
                print("Failed!")
                tm.print_debug(textwrap.indent(pprint.pformat(ret), " |"))

            return

        except ConnectionAbortedError:
            self.result.set(TestValue.FAILURE, "tcl_func aborted on stop request")
            print("tcl_func aborted on stop request.")
        except:
            traceback.print_exception(*sys.exc_info())
            if self.isStopped():
                self.result.set(TestValue.FAILURE, "tcl_func aborted on stop request")
            else:
                self.result.set(
                    TestValue.FAILURE,
                    'Unrecoverable "tcl_func" item error from {}'.format(self.func_name),
                )
