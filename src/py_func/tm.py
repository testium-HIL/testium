
import json
import sys
from py_func.handle import FuncHandler
from lib.tum_except import ETUMRuntimeError
from lib.api import SUPPORTED_API

thismodule = sys.modules[__name__]
_func_call_thread = None

# Local storage for non-JSON-serializable values
_local_dict = {}


def _is_json_serializable(value):
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False


###############################################################################
def _make_api(name):
    def _wrapper(*params):
        if _func_call_thread is not None:
            res = _func_call_thread.call(name, params)
            if "result" in res:
                ret_val = res["result"]
            elif "error" in res:
                raise ETUMRuntimeError(f"api call to 'tm.{name}' failed with error '{res["error"]}'")
            else:
                raise ETUMRuntimeError("api call failure in jrpc client to be reported to testium support team.")
            return ret_val
        else:
            raise ETUMRuntimeError("api not initialized")
    _wrapper.__name__ = name
    return _wrapper

for k in SUPPORTED_API:
    if k not in ('gd', 'setgd', 'delgd'):
        setattr(thismodule, k, _make_api(k))


###############################################################################
# gd/setgd/delgd with local-dict fallback for non-serializable values

def gd(*params):
    key = params[0] if params else None
    if key is not None and key in _local_dict:
        return _local_dict[key]
    if _func_call_thread is not None:
        res = _func_call_thread.call("gd", params)
        if "result" in res:
            return res["result"]
        elif "error" in res:
            raise ETUMRuntimeError(f"api call to 'tm.gd' failed with error '{res['error']}'")
        else:
            raise ETUMRuntimeError("api call failure in jrpc client to be reported to testium support team.")
    raise ETUMRuntimeError("api not initialized")


def setgd(*params):
    key = params[0] if params else None
    value = params[1] if len(params) > 1 else None
    if key is not None and not _is_json_serializable(value):
        _local_dict[key] = value
        return None
    if _func_call_thread is not None:
        res = _func_call_thread.call("setgd", params)
        if "result" in res:
            return res["result"]
        elif "error" in res:
            raise ETUMRuntimeError(f"api call to 'tm.setgd' failed with error '{res['error']}'")
        else:
            raise ETUMRuntimeError("api call failure in jrpc client to be reported to testium support team.")
    raise ETUMRuntimeError("api not initialized")


def delgd(*params):
    key = params[0] if params else None
    if key is not None and key in _local_dict:
        del _local_dict[key]
        return None
    if _func_call_thread is not None:
        res = _func_call_thread.call("delgd", params)
        if "result" in res:
            return res["result"]
        elif "error" in res:
            raise ETUMRuntimeError(f"api call to 'tm.delgd' failed with error '{res['error']}'")
        else:
            raise ETUMRuntimeError("api call failure in jrpc client to be reported to testium support team.")
    raise ETUMRuntimeError("api not initialized")


def _init_api(host, port, timeout):
    global _func_call_thread
    _func_call_thread = FuncHandler(host, port, timeout=timeout)
    return _func_call_thread


###############################################################################
def _remote_print(*values):
    if _func_call_thread is not None:
        try:
            _func_call_thread.call("print", values)
        except:
            pass


###############################################################################
class FunctionItem():
    """Class allowing extended capabilities of function."""
    module_count = 0

    def __init__(self):
        self._reported_value = {}

    def reportValue(self, key, value):
        self._reported_value[key] = value

    def reportedValues(self):
        return self._reported_value

    def exec(self):
        pass
