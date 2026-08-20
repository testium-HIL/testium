from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestResult, TestValue)
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.param_decl import ParamSet
from runtime.tum_except import ETUMSyntaxError
import api.testium as tm

class TestItemGroup(TestItem):

    # 'group' has no item-specific parameters; 'steps' is handled by COMMON_PARAMS.
    # Declaring an empty ParamSet still opts in to unknown-param validation
    # (e.g. typo 'stop_on_failures').
    PARAMS = ParamSet()

    def __init__(self, dict_cycle, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_GROUP.item_name
        super().__init__(dict_cycle, parent, status_queue, filename=filename)
        self._type = cst.TYPE_GROUP
        self.is_container = True
        self._is_step = False

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
                msg = 'Group execution aborted on failure'
                failing = self.__failing_child_name()
                if failing:
                    msg += " of step '{}'".format(failing)
                self.result.set(TestValue.FAILURE, msg)
            else:
                self.result.set(TestValue.NORUN, 'Group execution aborted on user request')
        else:
            self.result.set(TestValue.SUCCESS, '')
            for res in results:
                if not res.success:
                    failing = self.__failing_child_name()
                    self.result.set(
                        TestValue.FAILURE,
                        "Step '{}' failed".format(failing) if failing
                        else 'A child step failed')

    def __failing_child_name(self):
        """Name of the first failed child, for result messages only."""
        for j in range(self.childCount()):
            if self.child(j).result.test_result == TestValue.FAILURE:
                return self.child(j).name()
        return None
