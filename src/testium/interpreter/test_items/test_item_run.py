import os
from posixpath import splitext
import sys
import subprocess
from datetime import datetime
from time import sleep
import traceback

from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestValue)
import libs.testium as tm
from interpreter.utils.constants import TestItemType as cst
from lib.tum_except import ETUMSyntaxError, ETUMRuntimeError


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
        try:
            self.tum_fime = self._prms.getParam('tum_fime', required=True)
            self.param_file = self._prms.getParam('param_file', default='')
            self.python_bin = self._prms.getParam('python_bin', default='')
            self.testium_path = self._prms.getParam('testium_path', default='')
            self.log_path = self._prms.getParam('log_file', default='')
            self.report_path = self._prms.getParam('report_file', default='')
            self.start_time = self._prms.getParam('start_time')
            self.end_time = self._prms.getParam('end_time')
            self.wait_for_exec = self._prms.getParam('wait_for_exec')
        except:
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' has a missing or wrong parameter",
                self.seqFilename(),
            )

    @test_run
    def execute(self):
        res = -1
        try:
            file_path = self._prms.expanse(self.tum_fime)
            if not os.path.exists(file_path) and not os.path.isabs(file_path):
                file_path = os.path.join(tm.gd('test_directory'), self.tum_fime)
            if not os.path.isfile(file_path):
                raise ETUMRuntimeError(
                    '"{}" file could not be found'.format(file_path))
            self.tum_fime = file_path
            pf = self._prms.expanse(self.param_file)
            pp = self._prms.expanse(self.python_bin)
            sp = self._prms.expanse(self.testium_path)
            lp = self._prms.expanse(self.log_path)
            rp = self._prms.expanse(self.report_path)
            cmd = []
            if pp != '':
                cmd.append(pp)
            if sp == '':
                sp = os.path.join(tm.get_main_dir(), "testium.pyw")
            cmd.append(sp)
            if lp == '':
                lp = os.path.splitext(self.tum_fime)[0] + "_" + \
                    datetime.utcnow().isoformat(timespec='seconds') + '.log'
            cmd.append("-r")
            if pf != '':
                cmd.append("-c")
                cmd.append('"' + pf + '"')
            cmd.append("-l")
            cmd.append('"' + lp + '"')
            if rp != '':
                cmd.append("-p")
                cmd.append('"' + rp + '"')
            cmd.append(self.tum_fime)
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

            if self.wait_for_exec:
                while not nowInBetween(self.start_time, self.end_time):
                    sleep(60)
                r = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            elif self.start_time is not None and self.end_time is not None:
                if nowInBetween(self.start_time, self.end_time):
                    r = subprocess.run(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            elif self.start_time is not None:
                if self.start_time < datetime.now().time():
                    r = subprocess.run(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                r = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if isinstance(r, subprocess.CompletedProcess):
                print((r.stdout).decode())
                print(r.stderr.decode())
                res = r.returncode
            if res >= 0:
                self.result.set(TestValue.SUCCESS)
            else:
                self.result.set(TestValue.FAILURE,
                                'Test execution returned negative value.')
        except:
            traceback.print_exception(*sys.exc_info())
            self.result.set(TestValue.FAILURE, 'Unrecoverable "run" item error')


