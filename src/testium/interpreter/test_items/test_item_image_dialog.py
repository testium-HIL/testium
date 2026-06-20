import os

from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestValue
from interpreter.test_items.test_item_dialog_base import TestItemDialogBase, _is_text_mode, _is_interactive
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.param_decl import Param, ParamSet
from runtime.tum_except import item_load_context
import api.testium as tm


class TestItemImageDialog(TestItemDialogBase):
    """dialog_image item usage.
    dialog_image name: Nice image, question: could you press the red button, filename: img.jpg
    """

    PARAMS = ParamSet(
        Param("question", required=True,
              doc="Prompt shown above the image."),
        Param("filename", required=True,
              doc="Path to the image file (relative to the test directory or absolute)."),
        Param("auto_result", default=None,
              doc="Outcome used in batch/non-interactive mode. Truthy ⇒ SUCCESS, "
                  "None ⇒ FAILURE."),
    )

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_IMAGE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_IMAGE_DLG
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._question = self._prms.getParam("question", required=True)
            self._filename = self._prms.getParam("filename", required=True)
            self._auto_result = self._prms.getParam("auto_result", required=False, default=None)

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        image_path = self._prms.expanse(self._filename)
        print("Image Displayed:\n" + q + "\n" + image_path)
        if not os.path.isfile(image_path):
            image_path = os.path.normpath(
                os.path.join(tm.gd("test_directory"), image_path)
            )
        if _is_text_mode():
            if _is_interactive():
                ans = input("Accept? (y/n) [default: y]: ").strip().lower()
                self.result.set(TestValue.FAILURE if ans in ('n', 'no') else TestValue.SUCCESS)
            else:
                ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
                if ar is None:
                    self.result.set(TestValue.FAILURE, 'Dialog not supported in batch mode')
                elif ar == 'cancel':
                    self.result.set(TestValue.FAILURE)
                else:
                    self.result.set(TestValue.SUCCESS)
            return
        from interpreter.test_items.dialog_image_files import dialog_image
        ar = self._prms.expanse(self._auto_result) if self._auto_result is not None else None
        args = [self.name(), q, image_path] + ([ar] if ar is not None else [])
        succ = self._run_dialog_with_result(dialog_image.main, args)
        if succ is None:
            self.result.set(TestValue.FAILURE, "Dialog subprocess exited without returning a result")
        elif succ:
            self.result.set(TestValue.SUCCESS)
        else:
            self.result.set(TestValue.FAILURE)
