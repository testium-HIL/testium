
def donothing():
    return 0

def checkloopparam(loop_param):
    if not(loop_param==12 or loop_param==20 or loop_param==30):
        raise
    return 0

def checkloopindexes(loop_index, loop_index_inverse):
    # 5 iterations: inverse counts down 4..0, i.e. niter-1-index
    if loop_index_inverse != 4 - loop_index:
        raise
    return 0

def exitcondition(loop):
    if loop == 3:
        return True