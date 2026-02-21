import os, sys
import traceback
import multiprocessing

def exception_handler(typ_exc, value, trbk):
    """Testium Exception handling"""
    print(f"Critical failure : '{value}'.")
    tb = traceback.format_exception(typ_exc, value, trbk)
    print("".join(tb[-4:]))

sys.excepthook = exception_handler

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from testium import main

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        multiprocessing.freeze_support()
    main()