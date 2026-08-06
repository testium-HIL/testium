from interpreter.utils.py_process import PyProcessBase
from runtime.tum_except import ETUMRuntimeError
import api.testium as tm


eval_process = None


def eval_process_init(request_handler, timeout, python_path):
    global eval_process
    eval_process = EvalExecEngine(request_handler, timeout, python_path)
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
                raise ETUMRuntimeError(answer["error"])
            else:
                raise ETUMRuntimeError(
                    f"Malformed eval answer for '{value}': {answer}. "
                    "Internal error, please report it."
                )
        else:
            raise ETUMRuntimeError(
                f"The evaluation subprocess is not running (expression "
                f"'{value}'). It crashed, was stopped, or could not be "
                f"started — check the log above and the python_bin "
                f"interpreter '{self._pbin}'."
            )


def eval_exec(value):
    global eval_process
    if eval_process is not None and eval_process.is_alive():
        result = eval_process.eval(value)
    else:
        raise ETUMRuntimeError(
            f"The evaluation subprocess is not running (expression "
            f"'{value}'). It crashed, was stopped, or could not be "
            f"started — check the log above and the python_bin setting."
        )

    return result
