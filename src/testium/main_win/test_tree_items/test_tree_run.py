
from .test_tree_item import QTestTreeItem
from interpreter.utils.icons import icon_prefix

class QTestTreeItemRun(QTestTreeItem):
    def __init__(self, parent, test_set_item, cols):
        super().__init__(parent, test_set_item, cols)
        self.setRowIcon(icon_prefix() + "/testium_logo.svg")
