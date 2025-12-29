import py_func.tm as tm

class ValidationTest(tm.FunctionItem):
    def exec(self, param):
        print(str(param))
        return 0

