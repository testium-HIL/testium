import os
import sys
from multiprocessing import Process, Pipe

from interpreter.test_items.test_item import TestItem, test_run
from interpreter.test_items.test_result import TestResult, TestValue
from interpreter.test_items.dialog_image_files import dialog_image
import libs.testium as tm
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.tum_except import ETUMSyntaxError


class TestItemImageDialog(TestItem):
    """dialog_image item usage.
    dialog_image name: Nice image, question: could you press the red button, filename: img.jpg
    """

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_IMAGE_DLG.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_IMAGE_DLG
        self.is_container = False
        try:
            self._question = self._prms.getParam("question", required=True)
            self._filename = self._prms.getParam("filename", required=True)
        except:
            raise ETUMSyntaxError(
                f"The '{self.cmd()}' test item named '{self.name()}' has a missing or wrong parameter",
                self.seqFilename(),
            )

    @test_run
    def execute(self):
        ourpath = __file__
        test_file = os.path.join(
            os.path.dirname(ourpath), "dialog_image_files", "dialog_image.py"
        )

        q = self._prms.expanse(self._question)
        image_path = self._prms.expanse(self._filename)
        print("Image Displayed:\n" + q + "\n" + image_path)
        if not os.path.isfile(image_path):
            image_path = os.path.normpath(
                os.path.join(tm.gd("test_directory"), image_path)
            )

        parent_conn, child_conn = Pipe()
        p = Process(
            target=dialog_image.main, args=([self.name(), q, image_path], child_conn)
        )
        p.start()
        succ = parent_conn.recv()
        p.join()
        if succ:
            self.result.set(TestValue.SUCCESS)
        else:
            self.result.set(TestValue.FAILURE)


def mypath():
    if hasattr(sys, "frozen"):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


from multiprocessing import Process

if __name__ == "__main__":
    p = Process(target=test_dialog.main, args=(["bob", "bab"],))
    p.start()
    p.join()
