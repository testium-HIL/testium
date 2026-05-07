from pathlib import Path
import sys
import traceback

def exception_handler(typ_exc, value, trbk):
    """Testium Exception handling"""
    print("An unmanaged exception occured")
    print(f"Critical failure : '{value}'.")
    tb = traceback.format_exception(typ_exc, value, trbk)
    print("".join(tb))
    print(f"  python    : {sys.executable}")
    print(f"  sys.path  : {sys.path}")

sys.excepthook = exception_handler

# Make the parent directory of py_func/ (= the testium package dir, which also
# contains runtime/, lua_func/, …) the first entry on sys.path so `from py_func
# import main` and `from runtime…` resolve regardless of cwd or how this script
# was invoked. str() because some importers don't play well with PathLike entries.
_pkg_parent = str((Path(__file__).resolve().parent / "..").resolve())
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from py_func import main

if __name__ == '__main__':
    main()
