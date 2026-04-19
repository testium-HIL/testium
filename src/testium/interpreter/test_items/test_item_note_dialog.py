from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestValue
from interpreter.test_items.dialog_note_files import test_dialog
from interpreter.test_items.test_item_dialog_base import TestItemDialogBase
from interpreter.utils.constants import TestItemType as cst
from lib.tum_except import item_load_context
import libs.testium as tm


class TestItemNoteDialog(TestItemDialogBase):
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_NOTE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_NOTE_DLG
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._question = self._prms.getParam('question', required=True)

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        print("Question:\n" + q)
        result = self._run_dialog_with_result(test_dialog.main, [self.name(), q])
        if result is None:
            self.result.set(TestValue.FAILURE, "Dialog subprocess exited without returning a result")
            return
        val, succ = result
        tm.setgd(self.name(), val)
        print("\n" + ("-" * 80) + "\n")
        print("- Test note\n")
        print("-" * 80 + "\n")
        print(val)
        print("-" * 80 + "\n")
        self.result.reported = {'note': val}
        if succ:
            self.result.set(TestValue.SUCCESS, val)
        else:
            self.result.set(TestValue.FAILURE, val)
