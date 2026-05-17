from time import sleep

def dummy_exit(useless1, useless2):
    return True

def exit_exc(useless1, useless2):
    raise Exception('Crash of exit function')

def funcToBeExecuted (bla):
    print(bla)
    return bla

def funcToBeExecuted2 (bla):
    print(bla)
    return blo

def long_wait (sec):
    sleep(sec)