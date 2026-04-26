from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestValue
from interpreter.test_items.test_item_dialog_base import TestItemDialogBase, _is_text_mode, _is_interactive
from interpreter.utils.constants import TestItemType as cst
from lib.tum_except import item_load_context


class TestItemQuestionDialog(TestItemDialogBase):
    """dialog_question item usage.
    dialog_question name: Nice question, question: "If OK, press OK, If not, press cancel"
    """
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_QUESTION_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_QUESTION_DLG
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._question = self._prms.getParam('question', required=True)
            self._auto_result = self._prms.getParam('auto_result', required=False, default=None)

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        print('Question asked:\n' + q + '\n')
        if _is_text_mode():
            if _is_interactive():
                ans = input("Answer yes (y) or no (n) [default: y]: ").strip().lower()
            else:
                ans = ''
            if ans in ('n', 'no'):
                self.result.set(TestValue.FAILURE)
                print('Answer:    NO\n')
            else:
                self.result.set(TestValue.SUCCESS)
                print('Answer:    YES\n')
            return
        from interpreter.test_items.dialog_question_files import question_dialog
        ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
        args = [self.name(), q] + ([ar] if ar is not None else [])
        succ = self._run_dialog_with_result(question_dialog.main, args)
        if succ is None:
            self.result.set(TestValue.FAILURE, "Dialog subprocess exited without returning a result")
            return
        from PySide6.QtWidgets import QMessageBox
        if succ == QMessageBox.Yes:
            self.result.set(TestValue.SUCCESS)
            print('Answer:    YES\n')
        else:
            self.result.set(TestValue.FAILURE)
            print('Answer:    NO\n')
