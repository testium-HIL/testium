
import json
import sys
from py_func.handle import FuncHandler
from runtime.tum_except import ETUMRuntimeError
from runtime.api import SUPPORTED_API

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

def gd(name, default=None):
    """Return a value from the testium global dictionary.

    The value is accessible from any test item and from any ``py_func``
    subprocess, regardless of the ``context_id`` used.

    :param name: Name of the entry to retrieve.
    :type name: str
    :param default: Value returned when the key is absent. Defaults to ``None``.
    :return: The stored value, or *default* if not found.
    """
    if name is not None and name in _local_dict:
        return _local_dict[name]
    if _func_call_thread is not None:
        res = _func_call_thread.call("gd", (name, default))
        if "result" in res:
            return res["result"]
        elif "error" in res:
            raise ETUMRuntimeError(f"api call to 'tm.gd' failed with error '{res['error']}'")
        else:
            raise ETUMRuntimeError("api call failure in jrpc client to be reported to testium support team.")
    raise ETUMRuntimeError("api not initialized")


def setgd(name, value):
    """Store a value in the testium global dictionary.

    The stored value is accessible from any subsequent test item and from any
    ``py_func`` subprocess via :func:`gd`.

    When ``context_id`` is used on the ``py_func`` item, any Python object
    (including those that cannot be transmitted to other processes) can be
    stored and shared between calls running in the same subprocess.

    :param name: Name of the entry to set.
    :type name: str
    :param value: Value to store.
    """
    if name is not None and not _is_json_serializable(value):
        _local_dict[name] = value
        return None
    if _func_call_thread is not None:
        res = _func_call_thread.call("setgd", (name, value))
        if "result" in res:
            return res["result"]
        elif "error" in res:
            raise ETUMRuntimeError(f"api call to 'tm.setgd' failed with error '{res['error']}'")
        else:
            raise ETUMRuntimeError("api call failure in jrpc client to be reported to testium support team.")
    raise ETUMRuntimeError("api not initialized")


def delgd(name):
    """Remove an entry from the testium global dictionary.

    :param name: Name of the entry to remove.
    :type name: str
    """
    if name is not None and name in _local_dict:
        del _local_dict[name]
        return None
    if _func_call_thread is not None:
        res = _func_call_thread.call("delgd", (name,))
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
