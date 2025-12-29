import sys
import os
from multiprocessing import freeze_support
from itertools import chain

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox
from PySide6.QtCore import Qt, QSettings, QSize
from PySide6.QtGui import QFont, QFontInfo
from PySide6.QtWidgets import QTreeWidgetItem

# try:
from interpreter.test_items.dialog_choices_files import choices_dialog_win

# except:
#     import choices_dialog_win


def __iter__QTreeWidgetItem(self):
    for item in chain(*map(iter, self.children())):
        yield item
    yield self


def childrenQTreeWidgetItem(self):
    return [self.child(i) for i in range(self.childCount())]


QTreeWidgetItem.name = ""
QTreeWidgetItem.__iter__ = __iter__QTreeWidgetItem
QTreeWidgetItem.children = childrenQTreeWidgetItem


class ChoicesTreeItem(QTreeWidgetItem):

    def __init__(self, parent, dic, default_icon):
        super().__init__()
        self.name = dic.get("name", "")
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
        self.setCheckState(0, Qt.Checked)
        parent.addChild(self)
        self._default_icon = default_icon
        self.setRowIcon(dic.get("icon", ""))

    def setRowIcon(self, icon_path):
        icon = None
        if icon_path != "":
            if os.path.exists(icon_path):
                try:
                    pmap = QPixmap(icon_path)
                    icon = QIcon(pmap)
                    self.setIcon(0, icon)
                except:
                    # we don't want to crash for an icon
                    print(f"WARN  Impossible to load '{icon_path}' icon.")
        if (icon is None) and (self._default_icon is not None):
            self.setIcon(0, self._default_icon)


class ChoicesDialog(QDialog, choices_dialog_win.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self._default_icon = None
        self.setupUi(self)
        self.choicesView.setColumnCount(2)
        self.choicesView.setAlternatingRowColors(True)
        self.choicesView.setIconSize(QSize(24, 24))
        font = QFont()
        font.setPointSize(12)
        self.choicesView.setFont(font)
        self.choicesView.setAlternatingRowColors(True)
        self.choicesView.header().setVisible(True)
        self.choicesView.header().setDefaultSectionSize(50)
        self.choicesView.header().setMinimumSectionSize(50)
        self.choicesView.header().setStretchLastSection(False)

        self.choicesView.headerItem().setText(0, "name")
        self.choicesView.setColumnWidth(0, 300)
        self.choicesView.headerItem().setText(1, "description")
        self.choicesView.setColumnWidth(1, 800)
        self.root = self.choicesView.invisibleRootItem()

    def connect_checked(self):
        self.choicesView.itemChanged.connect(self.on_testChecked)

    def apply_default_icon(self, path):
        if (path is not None) and os.path.exists(path):
            try:
                pmap = QPixmap(path)
                self._default_icon = QIcon(pmap)
            except:
                # we don't want to crash for an icon
                print(f"WARN  Impossible to load '{path}' icon.")
        elif path is not None:
            print("Icon not loaded since it is not a valid path.")

    def populate_tree(self, parent, choices):
        if not isinstance(choices, list):
            return

        for choice in choices:
            name = choice.get("name", "")
            desc = choice.get("description", "")
            if name == "":
                continue
            tree_item = ChoicesTreeItem(parent, choice, self._default_icon)
            tree_item.setText(0, name)
            tree_item.setText(1, desc)
            sub_choices = choice.get("choices", None)
            if sub_choices is not None:
                self.populate_tree(tree_item, sub_choices)

    def __foldRecursively(self, tree_item, is_fold):
        for i in range(tree_item.childCount()):
            if tree_item.child(i).childCount() > 0:
                tree_item.child(i).setExpanded(not is_fold)
                self.__foldRecursively(tree_item.child(i), is_fold)

    def foldAll(self, is_fold):
        self.__foldRecursively(self.root, is_fold)

    def on_testChecked(self, item, index):
        self.updateTreeCheckState(item, Qt.Checked == item.checkState(0))

    def updateTreeCheckState(self, tree_item, is_checked):
        # treat the case of the invisible root
        if tree_item is self.root:
            for i in range(self.root.childCount()):
                self.updateTreeCheckState(self.root.child(i), is_checked)
        else:
            if is_checked:
                tree_item.setCheckState(0, Qt.Checked)
            else:
                tree_item.setCheckState(0, Qt.Unchecked)

            for i in range(tree_item.childCount()):
                self.updateTreeCheckState(tree_item.child(i), is_checked)

    def checked_state(self, parent=None):
        if parent is None:
            return self.checked_state(self.root)

        sub_choices = []
        for i in range(parent.childCount()):
            sub_choices.append(self.checked_state(parent.child(i)))

        if parent is self.root:
            res = sub_choices
        else:
            res = {
                "name": parent.name,
                "checked": Qt.Checked == parent.checkState(0),
            }
            if len(sub_choices) > 0:
                res.update({"choices": sub_choices})

        return res

    def apply_checked(self, choice, parent=None):
        if parent is None:
            self.apply_checked(choice, self.root)
            return

        if not isinstance(choice, list):
            return

        if len(choice) != parent.childCount():
            return

        for i in range(parent.childCount()):
            if not isinstance(choice[i], dict):
                return
            if choice[i].get("checked", True) == True:
                parent.child(i).setCheckState(0, Qt.Checked)
            else:
                parent.child(i).setCheckState(0, Qt.Unchecked)

            sub_choices = choice[i].get("choices", None)
            if sub_choices is not None:
                self.apply_checked(sub_choices, parent.child(i))


def main(args, conn=None):
    SettingsCompagny = "Testium"
    SettingsApplication = "testium_choices_dlg_" + args[0]
    SettingsLastChoices = "last_choice"
    success = True
    app = QApplication()
    d = ChoicesDialog()
    d.setFixedSize(800, 600)
    d.setWindowFlags(Qt.WindowStaysOnTopHint)
    d.setWindowTitle(args[0])
    d.labelDialog.setText(args[1])
    d.labelDialog.setAlignment(Qt.AlignCenter)
    d.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
    d.apply_default_icon(args[3])
    d.populate_tree(d.root, args[2])
    d.foldAll(False)

    settings = QSettings(SettingsCompagny, SettingsApplication)
    last_choice = settings.value(SettingsLastChoices, "")

    d.apply_checked(last_choice)

    d.connect_checked()

    d.choicesView.setFocus()
    dres = d.exec()

    if dres == QDialog.Rejected:
        success = False

    # build the answer:

    result = d.checked_state()

    if conn:
        settings.setValue(SettingsLastChoices, result)
        conn.send([result, success])
        conn.close()
    else:
        print(result, end="")

    if hasattr(sys, "frozen"):
        # all standard streams are replaced by dummy one to avoid cx_freeze flushing bug.
        class dummyStream:
            """dummyStream behaves like a stream but does nothing."""

            def __init__(self):
                pass

            def write(self, data):
                pass

            def read(self, data):
                pass

            def flush(self):
                pass

            def close(self):
                pass

        # and now redirect all default streams to this dummyStream:
        sys.stdout = dummyStream()
        sys.stderr = dummyStream()
        sys.stdin = dummyStream()
        sys.__stdout__ = dummyStream()
        sys.__stderr__ = dummyStream()
        sys.__stdin__ = dummyStream()


if __name__ == "__main__":
    main(sys.argv[1:])
