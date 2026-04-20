import multiprocessing

from interpreter.test_items.test_item import TestItem

_spawn_ctx = multiprocessing.get_context('spawn')


class TestItemDialogBase(TestItem):
    """Base class for test items that launch a Qt dialog in a subprocess."""

    def _cleanup_process(self, p):
        if p.is_alive():
            p.terminate()
            p.join(timeout=0.2)
            if p.is_alive():
                p.kill()
        p.join()

    def _run_dialog(self, target, args):
        """Launch target(args) in a subprocess with no return value.

        Returns the subprocess exit code.
        """
        p = _spawn_ctx.Process(target=target, args=(args,))
        p.start()
        while p.is_alive() and not self._is_stopped:
            p.join(timeout=0.5)
        self._cleanup_process(p)
        return p.exitcode

    def _run_dialog_with_result(self, target, args):
        """Launch target(args, child_conn) in a subprocess and return what it sends.

        Returns the received value, or None if stopped or if the subprocess crashed.
        """
        parent_conn, child_conn = _spawn_ctx.Pipe()
        p = _spawn_ctx.Process(target=target, args=(args, child_conn))
        p.start()
        child_conn.close()
        result = None
        while p.is_alive() and not self._is_stopped:
            if parent_conn.poll(0.5):
                result = parent_conn.recv()
                break
        self._cleanup_process(p)
        return result
