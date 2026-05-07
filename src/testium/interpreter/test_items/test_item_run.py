import os
from posixpath import splitext
import sys
import subprocess
from datetime import datetime
from time import sleep
import traceback

from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestValue)
import api.testium as tm
from interpreter.utils.constants import TestItemType as cst
from runtime.tum_except import ETUMSyntaxError, ETUMRuntimeError, item_load_context


def _testium_launch_cmd():
    """Command prefix to launch a fresh testium instance, runtime-aware.

    AppImage / Flatpak / PyInstaller / wheel / source all need a different
    entry point than just the path to __main__.py (which may be a .py inside
    a read-only bundle, or unreachable from the sub-instance's cwd).
    """
    # AppImage: the env var holds the path to the .AppImage file itself.
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        return [appimage]
    # Flatpak: re-launch via the Flatpak app id.
    if os.path.isfile("/.flatpak-info"):
        return ["flatpak", "run", "org.testium.Testium"]
    # PyInstaller frozen exe: sys.executable is the binary itself.
    if getattr(sys, "frozen", False):
        return [sys.executable]
    # Source / wheel: re-use the same Python with the same entry point that
    # launched this instance, made absolute so cwd changes in the sub-instance
    # don't break the lookup. argv[0] is either:
    #  - the package directory (source: `python3 src/testium ...`)
    #  - the console_scripts wrapper (wheel: `/usr/bin/testium`)
    # Both are runnable as `python <argv0>`.
    return [sys.executable, os.path.abspath(sys.argv[0])]


def nowInBetween(start, end):
    """
    Check wether current time is within boundaries
    """
    now = datetime.now().time()
    if start <= end:
        return start <= now < end
    else:
        return start <= now or now < end


class TestItemRun(TestItem):
    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_RUN.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_RUN
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self.tum_file = self._prms.getParam('tum', required=True)
            self.param_file = self._prms.getParam('param_file', default='')
            self.log_path = self._prms.getParam('log_file', default='')
            self.report_path = self._prms.getParam('report_file', default='')
            self.start_time = self._prms.getParam('start_time')
            self.end_time = self._prms.getParam('end_time')
            self.wait_for_exec = self._prms.getParam('wait_for_exec')

    @test_run
    def execute(self):
        try:
            file_path = self._prms.expanse(self.tum_file)
            if not os.path.exists(file_path) and not os.path.isabs(file_path):
                file_path = os.path.join(tm.gd('test_directory'), file_path)
            if not os.path.isfile(file_path):
                raise ETUMRuntimeError(
                    '"{}" file could not be found'.format(file_path))
            self.tum_file = file_path
            pf = self._prms.expanse(self.param_file)
            lp = self._prms.expanse(self.log_path)
            rp = self._prms.expanse(self.report_path)
            cmd = _testium_launch_cmd()
            if tm.text_mode():
                cmd.append("-b")
            else:
                cmd.append("-r")
                if lp == '':
                    lp = os.path.splitext(self.tum_file)[0] + "_" + \
                        datetime.utcnow().isoformat(timespec='seconds') + '.log'
                cmd.append("-l")
                cmd.append('"' + lp + '"')
            if pf != '':
                cmd.append("-c")
                cmd.append('"' + pf + '"')
            if rp != '':
                cmd.append("-p")
                cmd.append('"' + rp + '"')
            cmd.append(self.tum_file)
            for c in cmd:
                print(c, end = ' ')

            if self.start_time is not None:
                self.start_time = datetime.strptime(
                    self.start_time, '%H:%M').time()

            if self.end_time is not None:
                self.end_time = datetime.strptime(self.end_time, '%H:%M').time()

            if self.wait_for_exec and (self.start_time is None or self.end_time is None):
                raise ETUMRuntimeError(
                    '"wait_for_exec" set but not start_time or end_time')

            r = None
            if self.wait_for_exec:
                while not nowInBetween(self.start_time, self.end_time):
                    sleep(60)
                r = subprocess.run(cmd)
            elif self.start_time is not None and self.end_time is not None:
                if nowInBetween(self.start_time, self.end_time):
                    r = subprocess.run(cmd)
            elif self.start_time is not None:
                if self.start_time < datetime.now().time():
                    r = subprocess.run(cmd)
            else:
                r = subprocess.run(cmd)
            if isinstance(r, subprocess.CompletedProcess):
                self.result.set(TestValue.SUCCESS)
            else:
                self.result.set(TestValue.FAILURE, 'Sub-test did not execute')
        except:
            traceback.print_exception(*sys.exc_info())
            self.result.set(TestValue.FAILURE, 'Unrecoverable "run" item error')


