import py_func.tm as tm


def donothing():
    return 0


def checkloopparam(loop_param):
    if not (loop_param == 12 or loop_param == 20
            or loop_param == 30):
        raise
    return 0


def checkGlobalDic(param, expect):
    if tm.gd(param) != expect:
        raise Exception("Expected {} for {} but got {}".
                        format(expect, param, tm.gd(param)))
    return 0
