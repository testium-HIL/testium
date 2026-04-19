from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestValue
from interpreter.test_items.dialog_choices_files import choices_dialog
from interpreter.test_items.test_item_dialog_base import TestItemDialogBase
from interpreter.utils.constants import TestItemType as cst
from lib.tum_except import item_load_context
import libs.testium as tm


class TestItemChoicesDialog(TestItemDialogBase):
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_CHOICES_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_CHOICES_DLG
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._question = self._prms.getParam("question", required=True)
            self._choices = self._prms.getParam("choices", required=True)
            self._default_icon = self._prms.getParam("icon", required=False, default=None)

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        choices = self._prms.expanse(self._choices)
        icon = self._prms.expanse(self._default_icon)
        result = self._run_dialog_with_result(choices_dialog.main, [self.name(), q, choices, icon])
        if result is None:
            self.result.set(TestValue.FAILURE, "Dialog subprocess exited without returning a result")
            return
        val, succ = result
        self.result.value = val
        if succ:
            tm.setgd("cs_" + self._name, val)
            self.result.set(TestValue.SUCCESS, str(val))
        else:
            tm.delgd("cs_" + self._name)
            self.result.set(TestValue.FAILURE, str(val))
