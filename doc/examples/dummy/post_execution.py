
import py_func.tm as tm

def post_exec():
    print('Success !!!!')
    print(str(tm.gd('test_outputs')))

def post_exec_fail():
    print('Failure :(')
    print(str(tm.gd('test_outputs')))
