
from .test_tree_item import QTestTreeItem
from interpreter.utils.icons import icon_prefix

class QTestTreeItemJSONRPCAction(QTestTreeItem):
    def __init__(self, parent, test_set_item, cols):
        super().__init__(parent, test_set_item, cols)
        self.setRowIcon(icon_prefix() + "/JSON-LD.png")

class QTestTreeItemJSONRPC(QTestTreeItem):
    def __init__(self, parent, test_set_item, cols):
        super().__init__(parent, test_set_item, cols)
        self.recursive_unfoldable = False
        self.setRowIcon(icon_prefix() + "/JSON-LD.png")

