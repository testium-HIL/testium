import sys
import os

# Qt
from PySide6.QtGui import (QIcon, QPixmap)
from PySide6 import QtWidgets
from PySide6.QtWidgets import (QTreeWidget, QComboBox)
from PySide6.QtCore import (Signal, QSize, Qt)
from PySide6.QtGui import (QFont, QFontInfo)
from time import (time)

from main_win.test_tree_items.common import (TEST_COLS, TEST_COLS_WITH_TIME)
from interpreter.utils.tum_except import (ETUMFileError, ETUMSyntaxError)
from interpreter.utils.test_ctrl import TestSetController
from main_win.test_tree_items.test_tree_git import QTestTreeItemGit

# to be removed in the future and replaced by a more "sexy" mechanism
from main_win.test_tree_items.test_tree_unittest import (QTestTreeItemUnittest,
                                                         QTestTreeItemUnittestElement)
from main_win.test_tree_items.test_tree_sleep import QTestTreeItemSleep
from main_win.test_tree_items.test_tree_cycle import QTestTreeItemCycle
from main_win.test_tree_items.test_tree_group import QTestTreeItemGroup
from main_win.test_tree_items.test_tree_git import QTestTreeItemGit
from main_win.test_tree_items.test_tree_py_func import QTestTreeItemPyFunc
from main_win.test_tree_items.test_tree_lua_func import QTestTreeItemLuaFunc
from main_win.test_tree_items.test_tree_jsonrpc import QTestTreeItemJSONRPC, QTestTreeItemJSONRPCAction
from main_win.test_tree_items.test_tree_run import QTestTreeItemRun
from main_win.test_tree_items.test_tree_runtime_plot import QTestTreePlot, QTestTreePlotAction
from main_win.test_tree_items.test_tree_report import QTestTreeItemReport
from main_win.test_tree_items.test_tree_let import QTestTreeItemLet
from main_win.test_tree_items.test_tree_check import QTestTreeItemCheckValue
from main_win.test_tree_items.test_tree_unittest import QTestTreeItemUnittest, QTestTreeItemUnittestElement
from main_win.test_tree_items.test_tree_value_dialog import QTestTreeItemValueDialog
from main_win.test_tree_items.test_tree_note_dialog import QTestTreeItemNoteDialog
from main_win.test_tree_items.test_tree_image_dialog import QTestTreeItemImageDialog
from main_win.test_tree_items.test_tree_msg_dialog import QTestTreeItemMsgDialog
from main_win.test_tree_items.test_tree_question_dialog import QTestTreeItemQuestionDialog
from main_win.test_tree_items.test_tree_tested_references_dialog import QTestTreeItemTestedRefsDialog
from main_win.test_tree_items.test_tree_choices_dialog import QTestTreeItemChoicesDialog
from main_win.test_tree_items.test_tree_console import (QTestTreeItemConsole, QTestTreeItemConsoleAction)
from main_win.test_tree_items.test_tree_status_display import (QTestTreeItemStatusDisplay,
                                                               QTestTreeItemStatusDisplayDevice,
                                                               QTestTreeItemStatusDisplayTest)

from interpreter.test_items.test_result import (TestValue)
import libs.testium as tm
import interpreter.utils.settings as prefs
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.icons import icon_prefix

class QTestTree(QTreeWidget):
    breakpoint = Signal()
    DICT_TREE_ITEMS = {
                    cst.TYPE_UNITTEST_FILE.item_name    : QTestTreeItemUnittest,
                    cst.TYPE_UNITTEST_STEP.item_name    : QTestTreeItemUnittestElement,
                    cst.TYPE_SLEEP.item_name            : QTestTreeItemSleep,
                    cst.TYPE_CYCLE.item_name            : QTestTreeItemCycle,
                    cst.TYPE_GRAPH.item_name            : QTestTreePlot,
                    cst.TYPE_GRAPH_ACTION.item_name     : QTestTreePlotAction,
                    cst.TYPE_GROUP.item_name            : QTestTreeItemGroup,
                    cst.TYPE_GIT.item_name              : QTestTreeItemGit,
                    cst.TYPE_PY_FUNCTION.item_name      : QTestTreeItemPyFunc,
                    cst.TYPE_LUA_FUNCTION.item_name     : QTestTreeItemLuaFunc,
                    cst.TYPE_LET.item_name              : QTestTreeItemLet,
                    cst.TYPE_CHECK.item_name            : QTestTreeItemCheckValue,
                    cst.TYPE_JSON_RPC.item_name         : QTestTreeItemJSONRPC,
                    cst.TYPE_JSON_RPC_ACTION.item_name  : QTestTreeItemJSONRPCAction,
                    cst.TYPE_RUN.item_name              : QTestTreeItemRun,
                    cst.TYPE_REPORT.item_name           : QTestTreeItemReport,
                    cst.TYPE_VALUE_DLG.item_name        : QTestTreeItemValueDialog,
                    cst.TYPE_NOTE_DLG.item_name         : QTestTreeItemNoteDialog,
                    cst.TYPE_IMAGE_DLG.item_name        : QTestTreeItemImageDialog,
                    cst.TYPE_MESSAGE_DLG.item_name      : QTestTreeItemMsgDialog,
                    cst.TYPE_QUESTION_DLG.item_name     : QTestTreeItemQuestionDialog,
                    cst.TYPE_REFERENCE_DLG.item_name    : QTestTreeItemTestedRefsDialog,
                    cst.TYPE_CHOICES_DLG.item_name      : QTestTreeItemChoicesDialog,
                    cst.TYPE_CONSOLE.item_name          : QTestTreeItemConsole,
                    cst.TYPE_CONSOLE_ACTION.item_name   : QTestTreeItemConsoleAction,
                    'Status Display'                    : QTestTreeItemStatusDisplay,
                    'Device Status'                     : QTestTreeItemStatusDisplayDevice,
                    'Test Status'                       : QTestTreeItemStatusDisplayTest,
                    }
    def __init__(self, parent):

        super().__init__(parent)

        self.setAlternatingRowColors(True)
        self.setIconSize(QSize(18, 18))
        font = QFont()
        font.setPointSize(8)
        self.setFont(font)
        self.setAlternatingRowColors(True)
        self.setAnimated(True)
        self.setWordWrap(True)
        if prefs.settings.show_time_column:
            self.cols = TEST_COLS_WITH_TIME
        else:
            self.cols = TEST_COLS
        for k, v in prefs.settings.columns_size.items():
            if k in self.cols:
                self.cols[k]['size'] = v
        self.setColumnCount(len(self.cols))
        self.setObjectName("treeTests")
        self.header().setVisible(True)
        self.header().setCascadingSectionResizes(True)
        self.header().setDefaultSectionSize(50)
        self.header().setMinimumSectionSize(50)
        self.header().setStretchLastSection(False)
        self._global_success = True

        fi = QFontInfo(self.font())
        self._row_height = int(fi.pixelSize() * 2)
        self.setStyleSheet( ''' QTreeView::Item {{ height:{}px; }}'''.format(self._row_height))

        for name, data in self.cols.items():
            self.headerItem().setText(data['index'], data['name'])
            self.setColumnWidth(data['index'], data['size'])

        self.cycleIcon = QIcon()
        self.cycleIcon.addPixmap(QPixmap(icon_prefix() + "/cycle.png"))
        self.testIcon = QIcon()

        self.testStepIcon = QIcon()
        self.testStepIcon.addPixmap(QPixmap(icon_prefix() + "/document.png"))
        self.root = self.invisibleRootItem()

        self.header().sectionResized.connect(self.resized)

    def updateTestSetItemState(self, tree_item, tst_ctrl: TestSetController, state, unitary=False):
        id = tree_item.id
        tst_ctrl.control("set_enabled_state", item_id=id, enabled_state=state, unitary=unitary)

    def updateTreeCheckState(self, tree_item, tst_ctrl: TestSetController):
        # treat the case of the invisible root
        if tree_item is self.root:
            for i in range(self.root.childCount()):
                self.updateTreeCheckState(self.root.child(i), tst_ctrl)
        else:
            checked = tree_item.checkState(self.cols['name']['index'])
            state = (Qt.Checked == checked)
            self.updateTestSetItemState(tree_item, tst_ctrl, state)
            self.synchronizeEnabledState(tst_ctrl)

    def checkUncheckAll(self, tst_ctrl: TestSetController, isChecked):
        # test_set.enableDisableAll(test_set.rootItem(), isChecked)
        tst_ctrl.control("check_uncheck_all", checked=isChecked)
        self.synchronizeEnabledState(tst_ctrl)

    def __foldRecursively(self, tree_item, is_fold):
        for i in range(tree_item.childCount()):
            if tree_item.child(i).childCount() > 0 and tree_item.child(i).recursive_unfoldable :
                # GUI optimisation :
                # if you must fold everything, fold first the parent and then the childrens (1 GUI update)
                # if you must unfold everything, unfold first the childrens and then the parents (1 GUI update)
                if is_fold:
                    tree_item.child(i).setExpanded(not is_fold)
                    self.__foldRecursively(tree_item.child(i), is_fold)
                else:
                    self.__foldRecursively(tree_item.child(i), is_fold)
                    tree_item.child(i).setExpanded(not is_fold)

    def foldAll(self, is_fold):
        self.__foldRecursively(self.root, is_fold)

    def __synchronizeEnabledStateRecursively(self, tree_item, tst_ctrl: TestSetController):
        for i in range(tree_item.childCount()):
            id = tree_item.child(i).id
            checked = tst_ctrl.control("enabled_state", item_id=id)
            if checked:
                tree_item.child(i).setCheckState(self.cols['name']['index'],
                                                 Qt.Checked)
            else:
                tree_item.child(i).setCheckState(self.cols['name']['index'],
                                                 Qt.Unchecked)
            self.__synchronizeEnabledStateRecursively(
                tree_item.child(i), tst_ctrl)

    def updateTreeSkipState(self, tst_ctrl: TestSetController):
        self.__updateTreeSkipStateRecursively(self.root, tst_ctrl)

    def __updateTreeSkipStateRecursively(self, tree_item, tst_ctrl: TestSetController):
        for i in range(tree_item.childCount()):
            id = tree_item.child(i).id
            # skipped = test_set.getSkippedState(id)
            skipped = tst_ctrl.control("skipped_state", item_id=id)
            if skipped:
                tree_item.child(i).setDisabled(True)
                tree_item.child(i).setExpanded(False)
                tree_item.child(i)._is_skipped = True
                self.__skipRecursively(tree_item.child(i))
            else:
                tree_item.child(i)._is_skipped = False
                self.__updateTreeSkipStateRecursively(
                    tree_item.child(i), tst_ctrl)

    def __skipRecursively(self, tree_item):
        for i in range(tree_item.childCount()):
            tree_item.child(i).setDisabled(True)
            tree_item.child(i)._is_skipped = True
            self.__skipRecursively(tree_item.child(i))

    def synchronizeEnabledState(self, tst_ctrl: TestSetController):
        self.__synchronizeEnabledStateRecursively(self.root, tst_ctrl)

    def __enableRecursively(self, tree_item):
        for i in range(tree_item.childCount()):
            if not tree_item.child(i)._is_skipped:
                tree_item.child(i).setDisabled(False)
            self.__enableRecursively(tree_item.child(i))

    def setChildrenEnabled(self):
        self.__enableRecursively(self.root)

    def getGlobalSuccess(self):
        return self._global_success

    def clearGlobalSuccess(self):
        self._global_success = True

    def __findItemByIdRecursively(self, item_id, parent):
        res = None
        i = 0
        while (res is None) and (i < parent.childCount()):
            if parent.child(i).id == item_id:
                res = parent.child(i)
            i = i + 1

        i = 0
        while (res is None) and i < parent.childCount():
            res = self.__findItemByIdRecursively(item_id, parent.child(i))
            i = i + 1

        return res

    def __findItemById(self, item_id):
        item = self.__findItemByIdRecursively(
            item_id, self.invisibleRootItem())
        return item

    def __clearAllStatusRecursively(self, parent):
        for i in range(parent.childCount()):
            parent.child(i).clearStatus()
            # clear the combobox of results
            cb = self.itemWidget(parent.child(i), self.cols['desc']['index'])
            cb.clear()
            cb.addItem(' ')
            self.__clearAllStatusRecursively(parent.child(i))

    def clearAllStatus(self):
        root_item = self.invisibleRootItem()
        for i in range(root_item.childCount()):
            root_item.child(i).clearStatus()
            cb = self.itemWidget(root_item.child(
                i), self.cols['desc']['index'])
            cb.clear()
            cb.addItem(' ')
            self.__clearAllStatusRecursively(root_item.child(i))

    def updateStatus(self, status):
        if status['id'] > 0:
            item = self.__findItemById(status['id'])
            if item is not None:
                if 'value' in status:
                    # update the icon
                    is_success = status['value'] == TestValue.SUCCESS.value
                    is_norun = status['value'] == TestValue.NORUN.value
                    if is_success:
                        item.setStatusIcon(True)
                    elif not is_norun:
                        item.setStatusIcon(False)
                        self._global_success = False
                    # update the displayed message
                    if 'message' in status:
                        cb = self.itemWidget(item, self.cols['desc']['index'])
                        if (not is_success) and (not is_norun):
                            if not status['message'] == '':
                                cb.setItemText(0, status['message'])
                                cb.insertItem(
                                    1, status['date'] + ' ' + status['message'])
                        elif not is_norun:
                            cb.setItemText(0, status['message'])

                elif 'message' in status:
                    cb = self.itemWidget(item, self.cols['desc']['index'])
                    cb.setItemText(0, status['message'])

                if 'status' in status:
                    if status['status'].lower() == 'started':
                        if item.isBreakpoint():
                            self.breakpoint.emit()
                        item.setHighlighted()
                        item.setTimestamp(status['timestamp'])
                    else:
                        item.resetHighlighted()

                if ('duration' in status) and ('duration' in self.cols):
                    item.setText(self.cols['duration']['index'],
                                 '{:.1f}'.format(tm.timestamp_as_sec(status['duration'])))

    def loadTestRecursively(self, tree_parent, test_set_item):

        for test_id in test_set_item.keys():
            childType = test_set_item[test_id]["type"]
            if childType in self.DICT_TREE_ITEMS.keys():
                tree_item = self.DICT_TREE_ITEMS[childType](tree_parent,
                                                    test_set_item[test_id],
                                                    self.cols)
            else:
                raise ETUMSyntaxError(f"Error in the test_set, type {childType} undefined")

            cb = QComboBox(self)
            self.setItemWidget(tree_item, self.cols['desc']['index'], cb)
            cb.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            cb.setStyleSheet("""QComboBox {
                border-width: 1px;
                border-style: solid;
                border-radius: 4px;
                }""")
            cb.setEditable(False)
            cb.addItem(" ")
            cb.setMaxCount(1000)
            cb.setMaxVisibleItems(20)
            tree_item._failure_list = cb
            tree_item.is_folded = False
            if len(test_set_item[test_id]["child"]) > 0:
                tree_item.is_folded = test_set_item[test_id]["folded"]
                self.loadTestRecursively(tree_item,
                                         test_set_item[test_id]["child"])

    def removeCheckBoxes(self, root=None):
        if not root:
            root = self.invisibleRootItem()

        child_count = root.childCount()
        for i in range(child_count):
            item = root.child(i)
            if not item.checkState(0):
                item.setDisabled(True)
            item.setData(0, Qt.CheckStateRole, None)
            if root.child(i).childCount() > 0:
                self.removeCheckBoxes(root.child(i))

    def addCheckBoxes(self, root=None):
        if not root:
            root = self.invisibleRootItem()

        child_count = root.childCount()
        for i in range(child_count):
            item = root.child(i)
            item.setData(0, Qt.CheckStateRole, Qt.Checked)
            if root.child(i).childCount() > 0:
                self.addCheckBoxes(root.child(i))

    def showCheckBoxes(self, checklist, tst_ctrl: TestSetController):
        self.addCheckBoxes()
        self.restoreCheckList(checklist, tst_ctrl)

    def getItemCount(self):
        count = 0
        for i in self.root:
            count += 1
        return count

    def getFoldList(self):
        foldList = []
        for i in self.root:
            foldList.append(not i.isExpanded())
        return foldList

    def restoreFoldList(self, foldlist):
        itemlist = reversed(list(self.root))
        for item in itemlist:
            state = foldlist.pop(len(foldlist)-1)
            if item is not self.root:
                item.setExpanded(not state)

    def setFoldDefault(self):
        itemlist = list(self.root)
        for item in itemlist[:-1]:
            if item.is_folded:
                item.setExpanded(False)

    def getCheckList(self):
        checklist = []
        for i in self.root:
            checklist.append((i.checkState(0) == Qt.Checked))
        return checklist

    def restoreCheckList(self, checklist, tst_ctrl: TestSetController):
        itemlist = reversed(list(self.root))
        for item in itemlist:
            state = checklist.pop(len(checklist)-1)
            if item is not self.root:
                skipped = tst_ctrl.control("skipped_state", item_id=item.id)
                if skipped:
                    item.setDisabled(True)
                    for i in range(item.childCount()):
                        item.child(i).setExpanded(False)
                else:
                    if state:
                        item.setCheckState(
                            self.cols['name']['index'], Qt.Checked)
                    else:
                        item.setCheckState(
                            self.cols['name']['index'], Qt.Unchecked)
                    self.updateTestSetItemState(item, tst_ctrl, state, unitary=True)
                    # item.setDisabled(False)

    def resized(self, col, old_size, size):
        for k, v in self.cols.items():
            if v['index'] == col:
                self.cols[k]['size'] = size

    def saveSizes(self):
        sav = {}
        for k, v in self.cols.items():
            sav.update({k: self.cols[k]['size']})

        prefs.settings.columns_size = sav
