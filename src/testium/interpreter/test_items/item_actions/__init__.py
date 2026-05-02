from runtime.tum_except import ETUMSyntaxError
from interpreter.test_items.test_item import TestItem, test_run, test_data
from interpreter.test_items.test_result import TestResult, TestValue
from interpreter.test_items.item_actions.action import TestItemAction


class TestItemActions(TestItem):
    def __init__(
        self, item_type, dict_actions, parent=None, status_queue=None, filename=""
    ):
        self._name = item_type.item_name
        super().__init__(dict_actions, parent, status_queue, filename=filename)
        self._type = item_type
        self.is_container = False
        self.action_classes = {}
        self.actions_token = None
        self.actions = []
        try:
            self.dict_actions = dict_actions["steps"]
        except KeyError:
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' has no action list",
                self.seqFilename(),
            )

    def register_actions(self, **args: TestItemAction):
        for action_name, action_class in args.items():
            self.action_classes.update({action_name: action_class})

    def load(self):
        ret = {}
        for action in self.dict_actions:
            # Action should be only dict of length 1
            if not isinstance(action, dict) or (not len(action) == 1):
                raise ETUMSyntaxError(
                    f"The '{self.cmd()}' test item named '{self.name()}' action should be only dict of length = 1.",
                    self.seqFilename()
                )
            action_name = list(action.keys())[0]
            if not (action_name in self.action_classes.keys()):
                raise ETUMSyntaxError(
                    f"The '{self.cmd()}' test item named '{self.name()}' has an unknown action '{action.keys()[0]}'.",
                    self.seqFilename()
                )

            item = (self.action_classes[action_name])(
                action_name,
                action[action_name],
                self,
                self.status_queue,
                filename=self.seqFilename(),
            )
            self.actions.append(item)
            ret.update(test_data(item, {}))
        return ret

    def __run(self):
        results = []
        i = 0
        to_be_stopped = False
        while (
            (not self.isStopped()) and (i < self.childCount()) and (not to_be_stopped)
        ):
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

        result = TestResult(None, test_success, "Group iteration")
        return result

    def setSeqFilename(self, filename):
        super().setSeqFilename(filename)
        for action in self.actions:
            action.setSeqFilename(filename)

    @test_run
    def execute(self):
        results = []
        to_be_stopped = False
        if (not self.isStopped()) and (not to_be_stopped):
            result = self.__run()

            # Test results
            results.append(result)

            if result.test_result == TestValue.FAILURE and self._stop_on_failure:
                to_be_stopped = True

        # end of loop test
        if self.isStopped() or to_be_stopped:
            if to_be_stopped:
                self.result.set(
                    TestValue.FAILURE,
                    f"'{self._name}' item execution aborted on failure",
                )
            else:
                self.result.set(
                    TestValue.NORUN,
                    f"'{self._name}' item execution aborted on user request",
                )
        else:
            self.result.set(TestValue.SUCCESS, "")
            for res in results:
                if not res.success:
                    self.result.set(TestValue.FAILURE, "")
