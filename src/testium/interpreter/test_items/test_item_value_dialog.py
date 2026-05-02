from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestValue
from interpreter.test_items.test_item_dialog_base import TestItemDialogBase, _is_text_mode, _is_interactive
from interpreter.utils.constants import TestItemType as cst
from runtime.tum_except import item_load_context
import api.testium as tm


class TestItemValueDialog(TestItemDialogBase):
    """dialog_value item usage.
    dialog_value name: Enter value, question: "Which value did you measure?"
    """
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_VALUE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_VALUE_DLG
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._question = self._prms.getParam('question', required=True)
            self._default = self._prms.getParam('default', '')
            self._auto_result = self._prms.getParam('auto_result', required=False, default=None)
            self._auto_value = self._prms.getParam('auto_value', required=False, default=None)

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        d = self._prms.expanse(self._default)
        print("Question:\n" + q)
        if _is_text_mode():
            if _is_interactive():
                prompt = f"Enter value [{d}]: " if d else "Enter value: "
                ans = input(prompt).strip()
            else:
                ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
                av = self._prms.expanse(self._auto_value) if self._auto_value is not None else None
                if ar is None:
                    print("Answer: \nDialog not supported in batch mode")
                    self.result.set(TestValue.FAILURE, 'Dialog not supported in batch mode')
                    return
                if ar == 'cancel':
                    print("Answer: \nDialog cancelled")
                    self.result.set(TestValue.FAILURE, 'Dialog cancelled')
                    return
                ans = av if av is not None else ''
            val = ans if ans else d
            tm.setgd(self.name(), val)
            print("Answer: " + str(val))
            if val:
                self.result.reported = {'question': q, 'answer': val}
                self.result.value = val
                self.result.set(TestValue.SUCCESS, val)
            else:
                self.result.set(TestValue.FAILURE, 'No value entered')
            return
        from interpreter.test_items.dialog_value_files import test_dialog
        ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
        av = self._prms.expanse(self._auto_value) if self._auto_value is not None else None
        args = [self.name(), q, d] + ([ar, av] if ar is not None else [])
        result = self._run_dialog_with_result(test_dialog.main, args)
        if result is None:
            self.result.set(TestValue.FAILURE, "Dialog subprocess exited without returning a result")
            return
        val, succ = result
        tm.setgd(self.name(), val)
        print("Answer: " + val)
        if len(val) > 0:
            self.result.reported = {'question': q, 'answer': val}
            self.result.value = val
            if succ:
                self.result.set(TestValue.SUCCESS, val)
            else:
                self.result.set(TestValue.FAILURE, val)
        else:
            self.result.set(TestValue.FAILURE, 'The dialog did not return any value')
