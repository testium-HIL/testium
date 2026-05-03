from multiprocessing import Queue
from queue import Empty
from runtime.tum_except import ETUMRuntimeError


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
        # Drain stale responses (left over from earlier polled commands that
        # we had given up on waiting). They can land in the queue after our
        # clear() because the TestProcess may have pulled their request
        # before the clear, processed them, and pushed the response after.
        while True:
            res = self._test_resp.get(block, timeout)
            if isinstance(res, tuple):
                raise ETUMRuntimeError(f"Test set command '{cmd}' failed: '{res[1]}'")
            if isinstance(res, dict) and cmd in res.keys():
                return res[cmd]
            # Anything else is a stale response — discard and keep waiting.

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