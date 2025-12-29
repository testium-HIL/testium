
from .test_tree_item import QTestTreeItem
from interpreter.utils.icons import icon_prefix

class QTestTreeItemStatusDisplay(QTestTreeItem):
    def __init__(self, parent, test_set_item, cols):
        super().__init__(parent, test_set_item, cols)
        self.setRowIcon(icon_prefix() + "/checkList.png")
        self.setExpanded(True)

class QTestTreeItemStatusDisplayDevice(QTestTreeItem):
    def __init__(self, parent, test_set_item, cols):

        super().__init__(parent, test_set_item, cols)
        self.setRowIcon(icon_prefix() + "/RIOV-2478BF.PNG")
        self.setExpanded(True)

class QTestTreeItemStatusDisplayTest(QTestTreeItem):
    def __init__(self, parent, test_set_item, cols):
        super().__init__(parent, test_set_item, cols)
        self.setRowIcon(icon_prefix() + "/gears.png")
        self.setExpanded(True)


