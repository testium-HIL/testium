import random
import os
import sys
import time
import platform
import math
import json
import traceback
from testium.interpreter.utils.jrpc import JsonRpcSrv
from testium.interpreter.utils.tum_except import ETUMRuntimeError, print_exception
from py_func.func_call import func_exec


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
                        res, reported_values = func_exec(file, fname, args, verb)
                        return {
                            "result": {
                                "returned_value": res,
                                "reported_values": reported_values,
                            }
                        }
                    except TypeError as e:
                        return {
                            "error": f'In file "{file}",\ncalling function "{fname}" with bad arguments ({args}).\nMessage is "{str(e)}"'
                        }
                    except Exception as e:
                        tb = traceback.format_exc()
                        return {"error": "\n".join(tb.splitlines())}
                except Exception as e:
                    tb = traceback.format_exc()
                    return {
                        "error": f"bad jrpc req handler 'func_call' arguments ({"\n".join(tb.splitlines())}). To be reported to testium support team."
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
                            "error": f"Evaluation of '{value}' failed with message:\n  "+str(e)
                        }
                except Exception as e:
                    tb = traceback.format_exc()
                    return {
                        "error": f"bad jrpc req handler 'eval' arguments ({"\n".join(tb.splitlines())}). To be reported to testium support team."
                    }
            else:
                return {
                    "error": f"unknown RPC request ({method}). To be reported to testium support team."
                }
        except:
            print_exception(str(*sys.exc_info()))
            raise ETUMRuntimeError(
                "python Function item execution error. To be reported to testium support team."
            )
