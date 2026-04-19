import os

from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestValue
from interpreter.test_items.dialog_image_files import dialog_image
from interpreter.test_items.test_item_dialog_base import TestItemDialogBase
from interpreter.utils.constants import TestItemType as cst
from lib.tum_except import item_load_context
import libs.testium as tm


class TestItemImageDialog(TestItemDialogBase):
    """dialog_image item usage.
    dialog_image name: Nice image, question: could you press the red button, filename: img.jpg
    """
    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_IMAGE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_IMAGE_DLG
        self.is_container = False
        with item_load_context(self.cmd(), self.name(), self.seqFilename()):
            self._question = self._prms.getParam("question", required=True)
            self._filename = self._prms.getParam("filename", required=True)

    @test_run
    def execute(self):
        q = self._prms.expanse(self._question)
        image_path = self._prms.expanse(self._filename)
        print("Image Displayed:\n" + q + "\n" + image_path)
        if not os.path.isfile(image_path):
            image_path = os.path.normpath(
                os.path.join(tm.gd("test_directory"), image_path)
            )
        succ = self._run_dialog_with_result(dialog_image.main, [self.name(), q, image_path])
        if succ is None:
            self.result.set(TestValue.FAILURE, "Dialog subprocess exited without returning a result")
        elif succ:
            self.result.set(TestValue.SUCCESS)
        else:
            self.result.set(TestValue.FAILURE)
