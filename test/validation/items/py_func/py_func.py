import py_func.tm as tm

class ValidationTest(tm.FunctionItem):
    def exec(self, param):
        print(str(param))
        return 0

def donothing():
    return 0

def assertparam(param):
    assert param
    return 0

def checkglobal(param):
    assert param=='test parameter'
    return 0

def checkglobal2():
    return tm.gd("py_func test parameter")

def should_not_be_called(param):
    raise

def echo(param):
    return param

def tuple_return(first, second):
    return first, second

def set_context_value(val):
    tm.setgd("_py_ctx_test_value", val)
    return val

def get_context_value():
    return tm.gd("_py_ctx_test_value", None)


class _NotSerializable:
    def __init__(self, val):
        self.val = val

def set_ns_value(val):
    tm.setgd("_py_ctx_ns_value", _NotSerializable(val))
    return val

def get_ns_value():
    obj = tm.gd("_py_ctx_ns_value", None)
    return obj.val if obj is not None else None

def test_delgd():
    tm.setgd("_py_delgd_test", 42)
    assert tm.gd("_py_delgd_test") == 42
    tm.delgd("_py_delgd_test")
    assert tm.gd("_py_delgd_test", None) is None
    return 0
