
from interpreter.utils.py_process import PyProcessBase
from lib.tum_except import ETUMRuntimeError
from interpreter.test_items.test_result import TestValue


class PyFuncExecEngine(PyProcessBase):

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
                        "Unexepected py_func jrpc result. To be reported to testium support team."
                    )

            # In case an error was encountered in the called function
            elif "error" in answer:
                msg = f"{answer["error"]}"
                return TestValue.FAILURE, msg

            else:
                raise ETUMRuntimeError(
                    "Unexepected py_func call failure to be reported to testium support team."
                )
        else:
            raise ETUMRuntimeError(
                "No function execution process active. To be reported to testium support team."
            )
