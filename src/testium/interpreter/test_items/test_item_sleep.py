import re
from time import sleep
from datetime import timedelta
from multiprocessing import Process, Pipe

import libs.testium as tm
from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestValue)
from interpreter.utils.constants import TestItemType as cst
from lib.tum_except import ETUMSyntaxError, ETUMRuntimeError, item_load_context

class TestItemSleep(TestItem):
    """sleep item usage.
    sleep timeout: 10
    """

    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_SLEEP.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_SLEEP
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._timeout = self._prms.getParam('timeout', required=True)
            self._has_dialog = self._prms.getParam('dialog', default=False)

    @test_run
    def execute(self):

        timeout = self._prms.expanse(self._timeout)

        if isinstance(timeout, str) and timeout.isnumeric():
            timeout = float(timeout)
        elif isinstance(timeout, str):
            m = re.search(r"((?P<day>\d+)d)?\s*((?P<hour>\d+)h)?\s*((?P<minute>\d+)m)?\s*((?P<second>\d+)s)?", timeout, flags=re.IGNORECASE)
            if m.lastindex is not None :
                day = int(m.group("day")) if m.group("day") is not None else 0
                hour = int(m.group("hour")) if m.group("hour") is not None else 0
                minute = int(m.group("minute")) if m.group("minute") is not None else 0
                second = int(m.group("second")) if m.group("second") is not None else 0
                timeout = timedelta(days=day, hours=hour, minutes=minute, seconds=second).total_seconds()

        has_dialog = self._prms.expanse(self._has_dialog)

        #test core function
        if has_dialog:
            if tm.text_mode():
                import time as _time
                print(f"Sleep {timeout}s (press Ctrl+C to abort)...")
                end_time = _time.time() + float(timeout)
                while _time.time() < end_time and not self._is_stopped:
                    sleep(0.2)
                if self._is_stopped:
                    print("Aborted")
                    self.result.set(TestValue.FAILURE, 'Sleep aborted')
                else:
                    self.result.set(TestValue.SUCCESS, f'Sleep {timeout} sec')
                return

            from interpreter.test_items.dialog_sleep_files import dialog_sleep
            parent_conn, child_conn = Pipe()
            p=Process(target=dialog_sleep.main,  args=([self.name(), timeout],child_conn))
            p.start()
            succ = parent_conn.recv()
            p.join()

            if succ:
                mesg = 'Sleep %s sec' % (str(timeout))
                res = TestValue.SUCCESS
            else:
                mesg = 'Sleep aborted'
                print("Aborted")
                res = TestValue.FAILURE

            self.result.set(res, mesg)

        else:
            if not isinstance(timeout, (int, float)):
                raise ETUMRuntimeError(f"Timeout value of sleep test item \"{self.name}\" is not valid: \"{timeout}\".")
            import time as _time
            end_time = _time.time() + float(timeout)
            while _time.time() < end_time and not self._is_stopped:
                sleep(min(0.05, end_time - _time.time()))
            self.result.set(TestValue.SUCCESS, 'Sleep %s sec' % (str(timeout)))
