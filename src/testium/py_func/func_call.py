import sys
import importlib.util
import inspect
from pathlib import Path
import importlib
import traceback

from interpreter.utils.tum_except import ETUMRuntimeError, ETUMSyntaxError
from py_func import tm


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
        tb = traceback.format_exc()
        raise ETUMRuntimeError("Error importing file.\n" + "\n".join(tb.splitlines()))

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
                res = o.exec(*params)
                reported_values = o.reportedValues()

    if oldstyle:
        res = getattr(mod, func_name)(*params)

    reported_values.update({'returned': res})

    return res, reported_values