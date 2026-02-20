import sys
import traceback

import pprint
import textwrap

from interpreter.test_items.test_item import TestItem, test_run
from interpreter.test_items.test_result import TestValue
import libs.testium as tm
from interpreter.utils.lua_func_exec import LuaFuncExecEngine
from interpreter.utils.api_srv import api_request
from interpreter.utils.tum_except import ETUMSyntaxError, ETUMRuntimeError
from interpreter.utils.constants import TestItemType as cst


class TestItemLuaFunc(TestItem):
    """lua_func item usage.
    func file: func_file.lua, func_name: func, param: [$(variable1), [1, 2, 3], true]
    """

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_LUA_FUNCTION.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_LUA_FUNCTION
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
        # Lua functions call subprocess initialization
        self._lua_func_proc = LuaFuncExecEngine(tm.gd("lua_bin", ""), api_request, 10)

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

            self._lua_func_proc.start()
            if not self._lua_func_proc.wait_ready(10):
                raise ETUMRuntimeError(
                    f"""Impossible to start the external lua execution process.
Is the lua path correct ?
lua_bin = {tm.gd("lua_bin", "no lua path defined")}
Are "lua-sockets" and "lua-cjson" installed ?
Is the lua environnment well defined in the "LUA_PATH" and "LUA_CPATH" variables ?"""
                )

            try:
                success, ret = self._lua_func_proc.func_call(self.file_name, self.func_name, pl)
            finally:
                # Stops lua function execution process
                self._lua_func_proc.stop()
                self._lua_func_proc.join()

            if success == TestValue.SUCCESS:
                self.result.set(TestValue.SUCCESS)
                res, reported_values = ret
                reported_values = {**reported_values, "returned": res}
                self.result.reported = ret[1]
                print("Returned value:")
                print(textwrap.indent(pprint.pformat(res), " |"))

                # The result of the func test item is put in global dir and result
                tm.setgd("lfn_" + self._name, res)
                self.result.value = res

            else:
                self.result.set(TestValue.FAILURE, ret)
                print("Failed!")
                tm.print_debug(textwrap.indent(pprint.pformat(ret), " |"))

            return

        except:
            traceback.print_exception(*sys.exc_info())
            self.result.set(
                TestValue.FAILURE,
                'Unrecoverable "py_func" item error from {}'.format(self.func_name),
            )
