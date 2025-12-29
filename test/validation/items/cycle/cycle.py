
def donothing():
    return 0

def checkloopparam(loop_param):
    if not(loop_param==12 or loop_param==20 or loop_param==30):
        raise
    return 0

def exitcondition(loop):
    if loop == 3:
        return True