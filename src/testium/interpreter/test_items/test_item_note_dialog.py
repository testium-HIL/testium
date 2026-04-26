from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestValue
from interpreter.test_items.test_item_dialog_base import TestItemDialogBase, _is_text_mode, _is_interactive
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
            self._auto_result = self._prms.getParam('auto_result', required=False, default=None)
            self._auto_value = self._prms.getParam('auto_value', required=False, default=None)

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        print("Question:\n" + q)
        if _is_text_mode():
            if _is_interactive():
                print("Enter your note (type '.' on a new line to finish, empty line to cancel):")
                lines = []
                while True:
                    line = input()
                    if line == '.':
                        break
                    lines.append(line)
                val = '\n'.join(lines)
            else:
                ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
                av = self._prms.expanse(self._auto_value) if self._auto_value is not None else None
                if ar is None:
                    self.result.set(TestValue.FAILURE, 'Dialog not supported in batch mode')
                    return
                if ar == 'cancel':
                    self.result.set(TestValue.FAILURE, 'Dialog cancelled')
                    return
                val = av if av is not None else ''
            tm.setgd(self.name(), val)
            print("\n" + ("-" * 80) + "\n")
            print("- Test note\n")
            print("-" * 80 + "\n")
            print(val)
            print("-" * 80 + "\n")
            self.result.reported = {'note': val}
            if val:
                self.result.set(TestValue.SUCCESS, val)
            else:
                self.result.set(TestValue.FAILURE, val)
            return
        from interpreter.test_items.dialog_note_files import test_dialog
        ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
        av = self._prms.expanse(self._auto_value) if self._auto_value is not None else None
        args = [self.name(), q] + ([ar, av] if ar is not None else [])
        result = self._run_dialog_with_result(test_dialog.main, args)
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
