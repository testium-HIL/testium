"""tm — proxy module exposing remote-callable API functions.

This module dynamically exposes functions listed in
``interpreter.utils.api.SUPPORTED_API``. Each exposed function is a
thin wrapper that forwards the call to a running ``FuncHandler``
instance (stored in ``_func_call_thread``).

Typical usage:
    >>> from testium.py_func import tm
    >>> handler = tm._init_api(port)
    >>> tm.some_api_function(args)

Only after ``_init_api`` has been called will API functions be able to
send requests to the remote handler; otherwise an ``ETUMRuntimeError``
is raised.
"""

import sys
from py_func.handle import FuncHandler
from interpreter.utils.tum_except import ETUMRuntimeError
from interpreter.utils.api import SUPPORTED_API

thismodule = sys.modules[__name__]
# Shared FuncHandler instance used to forward API calls. Remains None
# until `_init_api` is invoked.
_func_call_thread = None


###############################################################################
# Dynamically create module-level functions for each supported API name.
# Each generated function shares the implementation of `api_call` but
# has a distinct name used as the remote action identifier.
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
    setattr(thismodule, k, _make_api(k))

def _init_api(port):
    """Start and initialize the remote function handler.

    Starts a ``FuncHandler`` bound to ``port``, runs it and blocks until
    it signals readiness.

    Args:
        port: port number or identifier passed to ``FuncHandler``.

    Returns:
        The initialized ``FuncHandler`` instance assigned to
        ``_func_call_thread``.
    """
    global _func_call_thread
    _func_call_thread = FuncHandler(port)
    _func_call_thread.start()
    _func_call_thread.wait_ready()
    return _func_call_thread


###############################################################################
def remote_print(*values):
    """Forward print-like output to the remote handler.

    If a ``_func_call_thread`` is available, this function calls the
    handler with action name ``"print"`` and the provided values. Errors
    during forwarding are ignored because printing is best-effort.
    """
    if _func_call_thread is not None:
        try:
            _func_call_thread.call("print", values)
        except:
            # Best-effort: ignore forwarding failures
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
