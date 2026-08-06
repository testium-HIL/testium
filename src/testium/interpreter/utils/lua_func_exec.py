
from interpreter.utils.lua_process import LuaProcessBase
from runtime.tum_except import ETUMRuntimeError
from interpreter.test_items.test_result import TestValue


class LuaFuncExecEngine(LuaProcessBase):

    def func_call(self, file: str, func_name: str, params: list, verbose: bool = True):
        if (self._rpc is not None) and self._rpc.is_alive():
            answer = self._rpc.call(
                "func_call",
                {
                    "file": file,
                    "fname": func_name,
                    "params": params,
                    "verbose": verbose,
                },
            )
            if "result" in answer:
                reported_values = answer["result"].get("reported_values", {})
                if "returned_value" in answer["result"]:
                    res = answer["result"]["returned_value"]
                    return TestValue.SUCCESS, (res, reported_values)
                else:
                    raise ETUMRuntimeError(
                        f"Malformed lua_func answer for '{func_name}' "
                        f"({file}): {answer}. Internal error, please "
                        "report it."
                    )

            # In case an error was encountered in the called function
            elif "error" in answer:
                msg = f"{answer['error']}"
                return TestValue.FAILURE, msg

            else:
                raise ETUMRuntimeError(
                    f"Malformed lua_func answer for '{func_name}' "
                    f"({file}): {answer}. Internal error, please report it."
                )
        else:
            raise ETUMRuntimeError(
                f"The lua_func subprocess is not running (function "
                f"'{func_name}', file '{file}'). It crashed, was stopped, "
                f"or could not be started — check the log above and the "
                f"lua_bin interpreter '{self._lbin}'."
            )

