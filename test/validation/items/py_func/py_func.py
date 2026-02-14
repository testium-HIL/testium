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

def should_not_be_called(param):
    raise

def echo(param):
    return param

def tuple_return(first, second):
    return first, second
