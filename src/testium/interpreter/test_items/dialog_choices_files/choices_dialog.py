import sys
import os
from multiprocessing import freeze_support

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                               QCheckBox, QHBoxLayout)
from PySide6.QtCore import Qt, QSettings, QTimer, QSize
from PySide6.QtGui import QFont, QFontInfo
from PySide6.QtWidgets import QTreeWidgetItem

# try:
from interpreter.test_items.dialog_choices_files import choices_dialog_win
from interpreter.utils import tree_states
from interpreter.test_items.dialog_choices_files import choices_presenter

# except:
#     import choices_dialog_win


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

        # Bulk controls above the tree, like the main window.
        self.checkSelect = QCheckBox("Select all / deselect all", self)
        self.checkSelect.setTristate(False)
        self.checkSelect.setChecked(True)
        self.checkSelect.stateChanged.connect(self.on_selectDeselectAll)
        self.checkFold = QCheckBox("Fold / Unfold", self)
        self.checkFold.setTristate(False)
        self.checkFold.stateChanged.connect(self.on_checkFoldChanged)
        controls_row = QHBoxLayout()
        controls_row.addWidget(self.checkSelect)
        controls_row.addWidget(self.checkFold)
        controls_row.addStretch(1)
        self.verticalLayout.insertLayout(1, controls_row)
        self.choicesView.itemCollapsed.connect(self.on_itemFoldChanged)
        self.choicesView.itemExpanded.connect(self.on_itemFoldChanged)

    def connect_checked(self):
        self.choicesView.itemChanged.connect(self.on_testChecked)

    def on_selectDeselectAll(self):
        state = self.checkSelect.checkState()
        self.choicesView.blockSignals(True)
        try:
            if state == Qt.Checked:
                self.updateTreeCheckState(self.root, True)
            elif state == Qt.Unchecked:
                self.updateTreeCheckState(self.root, False)
        finally:
            self.choicesView.blockSignals(False)

    def on_checkFoldChanged(self):
        if self.checkFold.checkState() != Qt.Unchecked:
            self.foldAll(True)
            self._set_silent(self.checkFold, Qt.Checked)
        else:
            self.foldAll(False)

    def on_itemFoldChanged(self):
        self._set_silent(self.checkFold, Qt.PartiallyChecked)

    @staticmethod
    def _set_silent(box, state):
        box.blockSignals(True)
        box.setCheckState(state)
        box.blockSignals(False)

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

    def foldAll(self, is_fold):
        # Blocked: a bulk fold must not flip checkFold to PartiallyChecked.
        self.choicesView.blockSignals(True)
        try:
            tree_states.fold_recursively(self.root, is_fold)
        finally:
            self.choicesView.blockSignals(False)

    def on_testChecked(self, item, index):
        self.choicesView.blockSignals(True)
        try:
            self.updateTreeCheckState(item, Qt.Checked == item.checkState(0))
        finally:
            self.choicesView.blockSignals(False)
        self._set_silent(self.checkSelect, Qt.PartiallyChecked)

    def updateTreeCheckState(self, tree_item, is_checked):
        state = Qt.Checked if is_checked else Qt.Unchecked
        if tree_item is self.root:
            for i in range(self.root.childCount()):
                tree_states.cascade_check(self.root.child(i), state)
        else:
            tree_states.cascade_check(tree_item, state)

    def checked_state(self, parent=None):
        return choices_presenter.checked_state(
            self.root, lambda item: Qt.Checked == item.checkState(0),
            is_root=True)

    def apply_checked(self, choice, parent=None):
        choices_presenter.apply_checked(
            choice, self.root,
            lambda item, checked: item.setCheckState(
                0, Qt.Checked if checked else Qt.Unchecked))

def main(args, conn=None):
    from interpreter.utils.settings import host_id
    SettingsCompagny = "Testium"
    # Per-host storage, like TestiumSettings (network home shared by PCs).
    SettingsApplication = "testium_choices_dlg_" + args[0] + "." + host_id()
    SettingsLastChoices = "last_choice"
    success = True
    from interpreter.test_items.dialog_presenter import (
        AUTO_CLOSE_MS, accepts, mute_frozen_streams)
    from interpreter.test_items import dialog_env
    dialog_env.setup()
    app = QApplication(['testium'])
    d = ChoicesDialog()
    d.resize(800, 600)
    d.setMinimumSize(500, 400)
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
    auto_result = args[4] if len(args) > 4 else None
    if auto_result is not None:
        QTimer.singleShot(AUTO_CLOSE_MS,
                          lambda: d.accept() if accepts(auto_result)
                          else d.reject())
    dres = d.exec()

    if dres == QDialog.Rejected:
        success = False

    # build the answer:

    result = d.checked_state()

    if conn:
        if result:
            # An empty tree yields [] — keep the previous selection instead
            # of locking every next dialog to its all-checked default.
            settings.setValue(SettingsLastChoices, result)
        # Flush before sending: the parent terminates this subprocess as soon
        # as it reads the result, so the QSettings destructor never runs and
        # the write would race the kill (lost under Flatpak — see the
        # tested-references dialog for the full rationale).
        settings.sync()
        conn.send([result, success])
        conn.close()
    else:
        print(result, end="")

    mute_frozen_streams()


if __name__ == "__main__":
    main(sys.argv[1:])
