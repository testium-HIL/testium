import os
import inspect
from pathlib import Path
import testium
from interpreter.utils.params import expanse

import libs.testium as tm


def testium_path():
    tp = inspect.getfile(inspect.getmodule(testium))
    return str(Path(tp).parent.resolve())


def prepare_file_to_save(file_name, file_ext=""):
    iname = file_name
    if file_ext != "":
        iname = os.path.splitext(file_name)[0] + file_ext

    if os.path.isfile(iname):
        i = 0
        fname = iname
        while os.path.isfile(fname):
            i += 1
            fname = iname + "-" + str(i) + ".saved"
        os.rename(iname, fname)
    return iname


def abs_path_from_file(file):
    abs_file_path = Path(expanse(file))
    if not abs_file_path.is_absolute():
        abs_file_path = Path(tm.gd("test_directory")) / abs_file_path
    abs_file_path = abs_file_path.resolve()
    return abs_file_path

