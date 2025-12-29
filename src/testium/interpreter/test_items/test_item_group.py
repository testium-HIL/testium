from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestResult, TestValue)
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.tum_except import ETUMSyntaxError
import libs.testium as tm

class TestItemGroup(TestItem):
    def __init__(self, dict_cycle, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_GROUP.item_name
        super().__init__(dict_cycle, parent, status_queue, filename=filename)
        self._type = cst.TYPE_GROUP
        self.is_container = True

    def __runALoop(self):
        results = []
        i = 0
        to_be_stopped = False
        while (not self.isStopped()) and (i < self.childCount()) and (not to_be_stopped):
            result = self.child(i).execute()
            results.append(result)
            if result.test_result == TestValue.FAILURE and self._stop_on_failure:
                to_be_stopped = True
            i = i + 1

        if self.isStopped() or to_be_stopped:
            for j in range(self.childCount()):
                if self.child(j).executedOnStop() and (j >= i):
                    self.child(j).execute()

        test_success = TestValue.SUCCESS
        for res in results:
            if res.test_result == TestValue.FAILURE:
                test_success = TestValue.FAILURE
                break

        result = TestResult(None, test_success, 'Group iteration')
        return result

    @test_run
    def execute(self):
        results = []
        to_be_stopped = False
        if (not self.isStopped()) and (not to_be_stopped):
            result = self.__runALoop()

            # Test results
            results.append(result)

            if result.test_result == TestValue.FAILURE and self._stop_on_failure:
                to_be_stopped = True

        # end of loop test
        if self.isStopped() or to_be_stopped:
            if to_be_stopped:
                self.result.set(TestValue.FAILURE, 'Group execution aborted on failure')
            else:
                self.result.set(TestValue.NORUN, 'Group execution aborted on user request')
        else:
            self.result.set(TestValue.SUCCESS, '')
            for res in results:
                if not res.success:
                    self.result.set(TestValue.FAILURE, '')
