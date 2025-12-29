
from .test_tree_item import QTestTreeItem
from interpreter.utils.icons import icon_prefix

class QTestTreeItemConsole(QTestTreeItem):
    def __init__(self, parent, test_set_item, cols):
        super().__init__(parent, test_set_item, cols)
        self.recursive_unfoldable = False
        self.setRowIcon(icon_prefix() + "/terminal.png")

class QTestTreeItemConsoleAction(QTestTreeItem):
    def __init__(self, parent, test_set_item, cols):
        super().__init__(parent, test_set_item, cols)

        self.setRowIcon(icon_prefix() + "/terminal.png")
