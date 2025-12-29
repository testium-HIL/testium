from multiprocessing import Queue
from queue import Empty
from interpreter.utils.tum_except import ETUMRuntimeError


class TestSetController:

    def __init__(self) -> None:
        self._test_ctrl = Queue()
        self._test_resp = Queue()

    @property
    def ctrl(self) -> Queue:
        return self._test_ctrl

    @property
    def resp(self) -> Queue:
        return self._test_resp

    def control(self, cmd: str, **args):
        block = True
        timeout = None
        if "block" in args:
            block = args.pop("block")
        if "timeout" in args:
            timeout = args.pop("timeout")
        self._test_ctrl.put({cmd: args})
        res = self._test_resp.get(block, timeout)
        if isinstance(res, tuple):
            raise ETUMRuntimeError(f"Test set command '{cmd}' failed: '{res[1]}'")
        if isinstance(res, dict) and not cmd in res.keys():
            raise ETUMRuntimeError(f"Unexpected return error in test set controller")
        return res[cmd]

    def clear(self):
        while True:
            try:
                self._test_ctrl.get_nowait()
            except Empty:
                # we return without error in that case
                break
        while True:
            try:
                self._test_resp.get_nowait()
            except Empty:
                # we return without error in that case
                break

    def close(self):
        self.ctrl.close()
        self.resp.close()