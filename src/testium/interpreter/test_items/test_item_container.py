from interpreter.test_items.test_item import TestItem, test_run
from interpreter.test_items.test_result import TestResult, TestValue


class TestItemContainer(TestItem):
    """Base class for items that run a sequence of children sequentially."""

    def __init__(self, item_type, dict_item, parent=None, status_queue=None, filename=""):
        self._name = item_type.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = item_type
        self.is_container = True

    def _run_children_sequentially(self):
        """Execute all children in order, respecting stop_on_failure and stop requests.
        Returns a TestResult aggregating all children outcomes."""
        i = 0
        to_be_stopped = False
        while not self.isStopped() and i < self.childCount() and not to_be_stopped:
            result = self.child(i).execute()
            if result.test_result == TestValue.FAILURE and self._stop_on_failure:
                to_be_stopped = True
            i += 1

        if self.isStopped() or to_be_stopped:
            for j in range(self.childCount()):
                if self.child(j).executedOnStop() and j >= i:
                    self.child(j).execute()

        success = TestValue.SUCCESS
        for j in range(i):
            if self.child(j).result.test_result == TestValue.FAILURE:
                success = TestValue.FAILURE
                break

        stopped = self.isStopped() or to_be_stopped
        return TestResult(None, success, ""), stopped
