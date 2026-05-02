from interpreter.utils.py_process import PyProcessBase
from runtime.tum_except import ETUMRuntimeError
import api.testium as tm


eval_process = None


def eval_process_init(python_bin, request_handler, timeout, python_path):
    global eval_process
    eval_process = EvalExecEngine(python_bin, request_handler, timeout, python_path)
    return eval_process


class EvalExecEngine(PyProcessBase):

    def eval(self, value):
        if (self._rpc is not None) and self._rpc.is_alive():
            answer = self._rpc.call(
                "eval",
                {
                    "value": value,
                },
            )
            if "result" in answer:
                return answer["result"]
                # In case an error was encountered in the called function
            elif "error" in answer:
                raise ETUMRuntimeError(answer["result"])
            else:
                raise ETUMRuntimeError(
                    "Unexepected eval call failure to be reported to testium support team."
                )
        else:
            raise ETUMRuntimeError(
                "No function execution process active. To be reported to testium support team."
            )


def eval_exec(value):
    global eval_process
    if eval_process is not None and eval_process.is_alive():
        result = eval_process.eval(value)
    else:
        raise ETUMRuntimeError(
            "No function execution process active. To be reported to testium support team."
        )

    return result
