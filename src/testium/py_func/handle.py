import random
import os
import sys
import time
import platform
import math
import json
import traceback

from runtime.jrpc import JsonRpcSrv
from runtime.tum_except import ETUMRuntimeError, print_exception
import py_func.tm as tm
from py_func.func_call import func_exec, format_user_traceback


# Port debugpy is listening on, set once per process (debugpy.listen can
# only be called once; the subprocess is shared when context_id is used).
_debug_bound_port = None


def _debug_attach(port):
    """Start the debugpy listener (once) and block until an IDE attaches.
    Raises ETUMRuntimeError with a user-oriented message on failure."""
    global _debug_bound_port
    try:
        import debugpy
    except ImportError:
        raise ETUMRuntimeError(
            "debugpy is not installed on the host interpreter used by "
            "testium (python_bin). Install it, e.g. "
            f"'{sys.executable} -m pip install debugpy'.")

    if _debug_bound_port is None:
        try:
            debugpy.listen(("localhost", port))
        except Exception as e:
            raise ETUMRuntimeError(
                f"debugpy could not listen on localhost:{port} ({e}). "
                "Is the port free? Change it with the 'py_func_debug_port' "
                "global.")
        _debug_bound_port = port
    elif port != _debug_bound_port:
        print(f"py_func: debug port already bound on localhost:"
              f"{_debug_bound_port} in this persistent process — ignoring "
              f"py_func_debug_port={port}")

    if debugpy.is_client_connected():
        print("py_func: debugger already attached.")
    else:
        print(f"py_func waiting for the debugger on localhost:"
              f"{_debug_bound_port} — attach from your IDE, or Stop to "
              "cancel")
        debugpy.wait_for_client()


class FuncHandler(JsonRpcSrv):

    def handle_request(self, method, params):
        try:
            if method == "func_call":
                try:
                    file = params["file"]
                    fname = params["fname"]
                    args = params["params"]
                    verb = params["verbose"]
                    try:
                        if params.get("debug"):
                            _debug_attach(params.get("debug_port", 5678))
                        res, reported_values = func_exec(file, fname, args, verb)
                        return {
                            "result": {
                                "returned_value": res,
                                "reported_values": reported_values,
                            }
                        }
                    except ETUMRuntimeError as e:
                        # Already a user-oriented message (bad signature,
                        # unknown function, import error).
                        return {"error": str(e)}
                    except Exception:
                        return {"error": format_user_traceback()}
                except Exception as e:
                    tb = traceback.format_exc()
                    return {
                        "error": "Malformed 'func_call' request arguments.\n"
                        + tb + "Internal error, please report it."
                    }
            if method == "eval":
                try:
                    value = params["value"]
                    try:
                        res = eval(value)
                        return {"result": res}
                    except Exception as e:
                        # eval can crash
                        return {
                            "error": f"Evaluation of the expression "
                            f"'{value}' (from a <| ... |> in the .tum) "
                            f"failed with {type(e).__name__}:\n  {e}"
                        }
                except Exception as e:
                    tb = traceback.format_exc()
                    return {
                        "error": "Malformed 'eval' request arguments.\n"
                        + tb + "Internal error, please report it."
                    }
            else:
                return {
                    "error": f"Unknown RPC request '{method}'. Internal "
                    "error, please report it."
                }
        except:
            tb = traceback.format_exc()
            print_exception(tb)
            raise ETUMRuntimeError(
                "Unhandled error in the py_func request handler.\n" + tb
                + "Internal error, please report it."
            )
