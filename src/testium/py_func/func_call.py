import sys
import importlib.util
import inspect
from pathlib import Path
import importlib
import traceback

from runtime.tum_except import ETUMRuntimeError, ETUMSyntaxError
from py_func import tm


def format_user_traceback():
    """Format the current exception, dropping the leading testium-internal
    frames so the traceback starts in the user's file."""
    etype, exc, tb = sys.exc_info()
    internal = {__file__, }
    try:
        import py_func.handle as _h
        internal.add(_h.__file__)
    except ImportError:
        pass
    def is_internal(t):
        f = t.tb_frame.f_code.co_filename
        return f in internal or f.startswith("<frozen importlib")

    while tb is not None and is_internal(tb):
        tb = tb.tb_next
    return "".join(traceback.format_exception(etype, exc, tb)).rstrip()


def check_signature(func, func_name, params, file):
    """Raise a clear error when params do not match the function signature.
    Checked before the call so a TypeError from the function body is not
    mistaken for a bad-arguments error."""
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return
    try:
        sig.bind(*params)
    except TypeError as e:
        raise ETUMRuntimeError(
            f'In file "{file}",\n'
            f'"{func_name}{sig}" cannot be called with param {params}:\n'
            f'  {e}')


def abs_path_from_file(file):
    abs_file_path = Path(file)
    if not abs_file_path.is_absolute():
        tdir = tm.gd("test_directory")
        abs_file_path = Path(tdir) / abs_file_path
    abs_file_path = abs_file_path.resolve()
    return abs_file_path


def func_module(file):
    abs_file_path = abs_path_from_file(file)

    if not abs_file_path.is_file():
        raise ETUMSyntaxError(f'"{abs_file_path}" file could not be found')

    try:
        sys.path.append(str(abs_file_path.parent))
        spec = importlib.util.spec_from_file_location(
            abs_file_path.stem,
            abs_file_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    except:
        raise ETUMRuntimeError(
            f'Error importing file "{abs_file_path}".\n'
            + format_user_traceback())

    return module


def func_exec(file: str, func_name: str, params: list, verbose: bool=True):
    """Executes a python function and returns its result and reported values
    """
    reported_values = {}
    mod = func_module(file)
    if verbose:
        print("Function executed from '{}'".format(
            inspect.getabsfile(mod)))

    # check of the FunctionItem descendants
    fitems = []
    for name, cls in inspect.getmembers(mod):
        if inspect.isclass(cls):
            if issubclass(cls, tm.FunctionItem):
                fitems.append(cls)

    oldstyle = True
    if len(fitems) > 0:
        for fitem in fitems:
            if fitem.__name__ == func_name:
                oldstyle = False
                o = fitem()
                check_signature(o.exec, func_name + ".exec", params, file)
                res = o.exec(*params)
                reported_values = o.reportedValues()

    if oldstyle:
        func = getattr(mod, func_name, None)
        if not callable(func):
            names = sorted(
                n for n, f in inspect.getmembers(mod, callable)
                if not n.startswith("_") and getattr(f, "__module__", None) == mod.__name__)
            raise ETUMRuntimeError(
                f'No function or FunctionItem class named "{func_name}" in '
                f'"{file}". Found: {", ".join(names) or "nothing"}.')
        check_signature(func, func_name, params, file)
        res = func(*params)

    reported_values.update({'returned': res})

    return res, reported_values