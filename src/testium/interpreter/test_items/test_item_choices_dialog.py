from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestValue
from interpreter.test_items.test_item_dialog_base import TestItemDialogBase, _is_text_mode, _is_interactive
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.param_decl import Param, ParamSet, BLOCK
from runtime.tum_except import item_load_context
import api.testium as tm


class TestItemChoicesDialog(TestItemDialogBase):

    PARAMS = ParamSet(
        Param("question", required=True,
              doc="Prompt shown above the list of choices."),
        Param("choices", kind=BLOCK, required=True,
              doc="Tree of choices: either a list of strings, or a nested "
                  "mapping {label: subchoices, ...} to build a multi-level menu."),
        Param("icon", default=None,
              doc="Default icon name shown next to each choice."),
        Param("auto_result", default=None,
              doc="Batch-mode selection (path or label). None ⇒ FAILURE."),
    )

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_CHOICES_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_CHOICES_DLG
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._question = self._prms.getParam("question", required=True)
            self._choices = self._prms.getParam("choices", required=True)
            self._default_icon = self._prms.getParam("icon", required=False, default=None)
            self._auto_result = self._prms.getParam("auto_result", required=False, default=None)

    def _print_choices(self, choices, indent=0):
        if not isinstance(choices, list):
            return
        for choice in choices:
            name = choice.get("name", "")
            desc = choice.get("description", "")
            line = "  " * indent + f"- {name}"
            if desc:
                line += f": {desc}"
            print(line)
            sub = choice.get("choices", None)
            if sub:
                self._print_choices(sub, indent + 1)

    def _all_checked(self, choices):
        result = []
        if not isinstance(choices, list):
            return result
        for choice in choices:
            item = {"name": choice.get("name", ""), "checked": True}
            sub = choice.get("choices", None)
            if sub is not None:
                item["choices"] = self._all_checked(sub)
            result.append(item)
        return result

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        choices = self._prms.expanse(self._choices)
        icon = self._prms.expanse(self._default_icon)
        if _is_text_mode():
            print(f"Choices: {q}")
            self._print_choices(choices)
            if _is_interactive():
                ans = input("Accept all? (y/n) [default: y]: ").strip().lower()
                if ans in ('n', 'no'):
                    tm.delgd("cs_" + self._name)
                    self.result.set(TestValue.FAILURE, "Cancelled")
                else:
                    val = self._all_checked(choices)
                    self.result.value = val
                    tm.setgd("cs_" + self._name, val)
                    self.result.set(TestValue.SUCCESS, str(val))
            else:
                ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
                if ar is None:
                    self.result.set(TestValue.FAILURE, 'Dialog not supported in batch mode')
                elif ar == 'cancel':
                    tm.delgd("cs_" + self._name)
                    self.result.set(TestValue.FAILURE, "Cancelled")
                else:
                    val = self._all_checked(choices)
                    self.result.value = val
                    tm.setgd("cs_" + self._name, val)
                    self.result.set(TestValue.SUCCESS, str(val))
            return
        from interpreter.test_items.dialog_choices_files import choices_dialog
        ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
        args = [self.name(), q, choices, icon] + ([ar] if ar is not None else [])
        result = self._run_dialog_with_result(choices_dialog.main, args)
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
