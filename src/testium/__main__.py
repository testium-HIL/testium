import os, sys
import logging
import traceback

logging.basicConfig(
    level=logging.ERROR,
    filename=os.path.join(os.path.normpath(os.getcwd()), "crash.txt"),
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def exception_handler(typ_exc, value, trbk):
    """Testium Exception handling"""
    logging.error("An unmanaged exception occured", exc_info=(typ_exc, value, trbk))
    print(f"Critical failure : '{value}'.")
    tb = traceback.format_exception(typ_exc, value, trbk)
    print("".join(tb[-4:]))

sys.excepthook = exception_handler

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from testium import main

if __name__ == '__main__':
    main()