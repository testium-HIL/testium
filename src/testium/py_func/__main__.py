from pathlib import Path
import sys
import traceback

def exception_handler(typ_exc, value, trbk):
    """Testium Exception handling"""
    print("An unmanaged exception occured", exc_info=(typ_exc, value, trbk))
    print(f"Critical failure : '{value}'.")
    tb = traceback.format_exception(typ_exc, value, trbk)
    print("".join(tb))

sys.excepthook = exception_handler

p = Path(__file__)
p = p.parent / ".."
p = p.resolve()

sys.path.append(p)

from py_func import main

if __name__ == '__main__':
    main()