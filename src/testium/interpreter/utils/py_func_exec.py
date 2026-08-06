
from interpreter.utils.py_process import PyProcessBase
from runtime.tum_except import ETUMRuntimeError
from interpreter.test_items.test_result import TestValue
import api.testium as tm


class PyFuncExecEngine(PyProcessBase):

    def func_call(self, file: str, func_name: str, params: list,
                  verbose: bool = True, debug: bool = False):
        if (self._rpc is not None) and self._rpc.is_alive():
            payload = {
                "file": file,
                "fname": func_name,
                "params": params,
                "verbose": verbose,
            }
            if debug:
                port = tm.gd("py_func_debug_port", 5678)
                try:
                    port = int(port)
                except (TypeError, ValueError):
                    raise ETUMRuntimeError(
                        f"The 'py_func_debug_port' global must be an integer "
                        f"(got '{port}').")
                payload["debug"] = True
                payload["debug_port"] = port
            answer = self._rpc.call("func_call", payload)
            if "result" in answer:
                reported_values = answer["result"].get("reported_values", {})
                if "returned_value" in answer["result"]:
                    res = answer["result"]["returned_value"]
                    return TestValue.SUCCESS, (res, reported_values)
                else:
                    raise ETUMRuntimeError(
                        f"Malformed py_func answer for '{func_name}' "
                        f"({file}): {answer}. Internal error, please "
                        "report it."
                    )

            # In case an error was encountered in the called function
            elif "error" in answer:
                msg = f"{answer['error']}"
                return TestValue.FAILURE, msg

            else:
                raise ETUMRuntimeError(
                    f"Malformed py_func answer for '{func_name}' "
                    f"({file}): {answer}. Internal error, please report it."
                )
        else:
            raise ETUMRuntimeError(
                f"The py_func subprocess is not running (function "
                f"'{func_name}', file '{file}'): crashed, stopped or never "
                f"started. python_bin: '{self._pbin}'."
            )
