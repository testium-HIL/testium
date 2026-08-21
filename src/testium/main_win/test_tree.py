import sys
import os

# Qt
from PySide6.QtGui import (QIcon, QPixmap, QCursor)
from PySide6 import QtWidgets
from PySide6.QtWidgets import (QTreeWidget, QMenu, QApplication)
from PySide6.QtCore import (Signal, QSize, Qt)

from gui.result_history import ResultHistory
from main_win.test_tree_items.common import make_columns
from runtime.tum_except import (ETUMFileError, ETUMSyntaxError)
from main_win.test_controller_service import TestControllerService
from main_win.test_tree_items.test_tree_item import make_tree_item

from interpreter.test_items.test_result import (TestValue)
import api.testium as tm
import interpreter.utils.settings as prefs
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.icons import icon_prefix

class QTestTree(QTreeWidget):
    # Emitted when the engine reports an item paused (breakpoint, step,
    # run-level pause, jump arrival).
    paused = Signal()
    # Emitted when a manual scroll disengages the follow-run mode.
    follow_disengaged = Signal()

    _KNOWN_TYPES = {e.item_name for e in cst}


    def __init__(self, parent):

        super().__init__(parent)

        self.setAlternatingRowColors(True)
        self.setIconSize(QSize(18, 18))
        font = self.font()
        font.setPointSizeF(max(7.0, font.pointSizeF() - 1))
        self.setFont(font)
        self.setAnimated(True)
        self.result_history = ResultHistory()
        self.cols = make_columns()
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

        for name, data in self.cols.items():
            self.headerItem().setText(data['index'], data['name'])
            self.setColumnWidth(data['index'], data['size'])

        # Breakpoint gutter: the pause column moves to the far left (visual
        # order only, logical indexes are untouched) while the tree structure
        # (arrows, indentation, checkboxes) stays on the name column.
        pause_col = self.cols['pause']['index']
        self.setTreePosition(self.cols['name']['index'])
        self.header().moveSection(self.header().visualIndex(pause_col), 0)
        # Narrowest width showing the full dot: the item delegate offsets the
        # icon by PM_FocusFrameHMargin + 1 from the cell edge (style
        # dependent), then draws it at iconSize.
        margin = self.style().pixelMetric(
            QtWidgets.QStyle.PM_FocusFrameHMargin, None, self) + 1
        gutter_width = margin + self.iconSize().width()
        self.header().setMinimumSectionSize(gutter_width)
        self.header().setSectionResizeMode(pause_col, QtWidgets.QHeaderView.Fixed)
        self.setColumnWidth(pause_col, gutter_width)

        self.cycleIcon = QIcon()
        self.cycleIcon.addPixmap(QPixmap(icon_prefix() + "/cycle.png"))
        self.testIcon = QIcon()

        self.testStepIcon = QIcon()
        self.testStepIcon.addPixmap(QPixmap(icon_prefix() + "/document.png"))
        self.root = self.invisibleRootItem()

        self.set_time_column_visible(prefs.settings.show_time_column)
        self.header().sectionResized.connect(self.resized)
        self.itemClicked.connect(self._on_result_clicked)
        self._follow = False
        self.verticalScrollBar().sliderPressed.connect(
            self._disengage_follow)

    def set_follow(self, enabled):
        self._follow = bool(enabled)

    def _disengage_follow(self):
        if self._follow:
            self._follow = False
            self.follow_disengaged.emit()

    def wheelEvent(self, event):
        self._disengage_follow()
        super().wheelEvent(event)

    def set_time_column_visible(self, visible):
        self.setColumnHidden(self.cols['duration']['index'], not bool(visible))

    def _on_result_clicked(self, item, column):
        """Dated failure history of the Result column, newest first; a
        picked entry is copied to the clipboard."""
        if column != self.cols['desc']['index']:
            return
        entries = self.result_history.entries(item.id)
        if not entries:
            return
        menu = QMenu(self)
        for date, message in entries[:20]:
            action = menu.addAction(
                f"{date}  " + " ".join(message.split()))
            action.setData(f"{date}  {message}")
        chosen = menu.exec(QCursor.pos())
        if chosen is not None:
            QApplication.clipboard().setText(chosen.data())

    def _refresh_result(self, item):
        text = self.result_history.current(item.id)
        idx = self.cols['desc']['index']
        # One line whatever the message: multi-line text would change the
        # row height. The full text stays in the tooltip and the history.
        item.setText(idx, " ".join(text.split()))
        item.setToolTip(idx, text if text else None)

    def updateTestSetItemState(self, tree_item, tst_ctrl: TestControllerService, state, unitary=False):
        id = tree_item.id
        tst_ctrl.set_enabled_state(id, state, unitary=unitary)

    def updateTreeCheckState(self, tree_item, tst_ctrl: TestControllerService):
        # treat the case of the invisible root
        if tree_item is self.root:
            for i in range(self.root.childCount()):
                self.updateTreeCheckState(self.root.child(i), tst_ctrl)
        else:
            checked = tree_item.checkState(self.cols['name']['index'])
            state = (Qt.Checked == checked)
            self.updateTestSetItemState(tree_item, tst_ctrl, state)
            self.synchronizeEnabledState(tst_ctrl)

    def checkUncheckAll(self, tst_ctrl: TestControllerService, isChecked):
        # test_set.enableDisableAll(test_set.rootItem(), isChecked)
        tst_ctrl.check_uncheck_all(isChecked)
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

    def __synchronizeEnabledStateRecursively(self, tree_item, states):
        for i in range(tree_item.childCount()):
            child = tree_item.child(i)
            checked = states.get(child.id, True)
            child.setCheckState(self.cols['name']['index'],
                                Qt.Checked if checked else Qt.Unchecked)
            self.__synchronizeEnabledStateRecursively(child, states)

    def updateTreeSkipState(self, tst_ctrl: TestControllerService):
        self.__updateTreeSkipStateRecursively(self.root, tst_ctrl)

    def __updateTreeSkipStateRecursively(self, tree_item, tst_ctrl: TestControllerService):
        for i in range(tree_item.childCount()):
            id = tree_item.child(i).id
            # skipped = test_set.getSkippedState(id)
            skipped = tst_ctrl.get_skipped_state(id)
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

    def synchronizeEnabledState(self, tst_ctrl: TestControllerService):
        # One round-trip for the whole tree (the engine cascades states).
        states = tst_ctrl.get_enabled_states()
        self.__synchronizeEnabledStateRecursively(self.root, states)

    def getGlobalSuccess(self):
        return self._global_success

    def clearGlobalSuccess(self):
        self._global_success = True

    def _all_items(self):
        """Pre-order (visual, top-to-bottom) iteration over every tree item."""
        def walk(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                yield child
                yield from walk(child)
        yield from walk(self.invisibleRootItem())

    def clearHighlights(self):
        """Drop the current-item highlight everywhere. Needed after a stop
        while paused: the paused item never gets its end-of-run status, so
        updateStatus() never resets it."""
        # Block signals: setBackground -> itemChanged -> on_testChecked storm.
        self.blockSignals(True)
        try:
            for it in self._all_items():
                it.resetHighlighted()
        finally:
            self.blockSignals(False)

    def clear_search(self):
        # Block signals: setBackground -> itemChanged -> on_testChecked storm.
        self.blockSignals(True)
        try:
            for it in self._all_items():
                it.setSearchMatch(False)
        finally:
            self.blockSignals(False)

    def search(self, text, fields):
        """Highlight items matching *text* in *fields*, expand ancestors, return matches."""
        matches = []
        text = (text or "").strip()
        needle = text.lower()
        active = bool(text and fields)
        # One blocked pass: clear stale + set new matches without firing signals.
        self.blockSignals(True)
        try:
            for it in self._all_items():
                matched = active and it.matches_search(needle, fields)
                it.setSearchMatch(matched)
                if matched:
                    matches.append(it)
                    p = it.parent()
                    while p is not None:
                        self.expandItem(p)
                        p = p.parent()
        finally:
            self.blockSignals(False)
        return matches

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
            parent.child(i).setText(self.cols['desc']['index'], "")
            parent.child(i).setToolTip(self.cols['desc']['index'], None)
            self.__clearAllStatusRecursively(parent.child(i))

    def clearAllStatus(self):
        # Signals stay connected at run start: item writes must not fire
        # itemChanged.
        self.blockSignals(True)
        try:
            self.result_history.clear()
            self.__clearAllStatusRecursively(self.invisibleRootItem())
        finally:
            self.blockSignals(False)

    def updateStatus(self, status):
        if status['id'] > 0:
            item = self.__findItemById(status['id'])
            if item is not None:
                # Signals stay connected during a run (live checkboxes):
                # setBackground/setText on the name column must not fire
                # itemChanged. The paused signal is emitted after unblocking.
                emit_paused = False
                self.blockSignals(True)
                try:
                    self.__updateStatusItem(item, status)
                    if status.get('status', '').lower() == 'paused':
                        emit_paused = True
                finally:
                    self.blockSignals(False)
                if emit_paused:
                    self.paused.emit()

    def __updateStatusItem(self, item, status):
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
                if (not is_success) and (not is_norun):
                    if not status['message'] == '':
                        self.result_history.record_failure(
                            item.id, status['date'], status['message'])
                elif not is_norun:
                    self.result_history.set_current(
                        item.id, status['message'])
                self._refresh_result(item)

        elif 'message' in status:
            self.result_history.set_current(item.id, status['message'])
            self._refresh_result(item)

        if 'status' in status:
            st = status['status'].lower()
            if st == 'started':
                item.setHighlighted()
                item.setTimestamp(status['timestamp'])
                if self._follow:
                    # Respect the user's folds: never expand — follow the
                    # topmost collapsed ancestor instead.
                    target = item
                    parent = item.parent()
                    while parent is not None:
                        if not parent.isExpanded():
                            target = parent
                        parent = parent.parent()
                    self.scrollToItem(
                        target, QTreeWidget.ScrollHint.PositionAtCenter)
            elif st != 'paused':
                item.resetHighlighted()

        if ('duration' in status) and ('duration' in self.cols):
            item.setText(self.cols['duration']['index'],
                         '{:.1f}'.format(tm.timestamp_as_sec(status['duration'])))

    def loadTestRecursively(self, tree_parent, test_set_item):

        for test_id in test_set_item.keys():
            childType = test_set_item[test_id]["type"]
            if childType not in self._KNOWN_TYPES:
                item_name = test_set_item[test_id].get("name", test_id)
                raise ETUMSyntaxError(
                    f"Error in the test_set: item '{item_name}' has "
                    f"undefined type '{childType}'")
            tree_item = make_tree_item(tree_parent, test_set_item[test_id], self.cols)
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
            # PySide6 enums are truthy even for Unchecked (value 0): compare
            # explicitly. PartiallyChecked parents stay enabled.
            if item.checkState(0) == Qt.Unchecked:
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

    def getItemCount(self):
        count = 0
        for i in self.root:
            count += 1
        return count

    def setFoldDefault(self):
        itemlist = list(self.root)
        for item in itemlist[:-1]:
            if item.is_folded:
                item.setExpanded(False)

    # --- Path-keyed item states (fold/check/breakpoint) -----------------------
    # Reload and startup restoration matches items by a path key instead of
    # positional lists.

    def _walk_with_keys(self, parent=None, prefix=()):
        """Yield (item, key) for every item. Key = tuple of (type, name, occ)
        components from root to item; occ counts the preceding siblings with
        the same (type, name), so unrelated insertions don't shift keys."""
        if parent is None:
            parent = self.invisibleRootItem()
        seen = {}
        for i in range(parent.childCount()):
            item = parent.child(i)
            ident = (item.test_type, item.name or "")
            occ = seen.get(ident, 0)
            seen[ident] = occ + 1
            key = prefix + (ident + (occ,),)
            yield item, key
            yield from self._walk_with_keys(item, key)

    def getItemStates(self):
        """One [key, folded, checked, breakpoint, bp_condition] entry per
        item. JSON-compatible: feeds both the reload snapshot and the
        settings."""
        states = []
        for item, key in self._walk_with_keys():
            states.append([
                [list(c) for c in key],
                not item.isExpanded(),
                item.checkState(0) == Qt.Checked,
                item.isBreakpoint(),
                getattr(item, "_bp_condition", None),
            ])
        return states

    def restoreItemStates(self, states, tst_ctrl: TestControllerService,
                          apply_check: bool):
        """Restore fold/check/breakpoint by path key. Items whose key is
        absent keep their defaults; obsolete keys are dropped. Breakpoints
        and enabled states are re-issued with the new interpreter ids.
        Length-tolerant: entries saved without bp_condition load unchanged."""
        wanted = {}
        for entry in states:
            key, folded, checked, breakpoint = entry[:4]
            condition = entry[4] if len(entry) > 4 else None
            wanted[tuple(tuple(c) for c in key)] = (
                folded, checked, breakpoint, condition)
        for item, key in self._walk_with_keys():
            state = wanted.get(key)
            if state is None:
                continue
            folded, checked, breakpoint, condition = state
            item.setExpanded(not folded)
            if apply_check:
                if tst_ctrl.get_skipped_state(item.id):
                    item.setDisabled(True)
                    for i in range(item.childCount()):
                        item.child(i).setExpanded(False)
                else:
                    item.setCheckState(
                        self.cols['name']['index'],
                        Qt.Checked if checked else Qt.Unchecked)
                    self.updateTestSetItemState(item, tst_ctrl, checked,
                                                unitary=True)
            if breakpoint and not item._no_breakpoint:
                item.setBreakpointState(True, condition)
                tst_ctrl.add_breakpoint(item.id, condition=condition)

    def resized(self, col, old_size, size):
        for k, v in self.cols.items():
            if v['index'] == col:
                self.cols[k]['size'] = size

    def saveSizes(self):
        sav = {}
        for k, v in self.cols.items():
            sav.update({k: self.cols[k]['size']})

        prefs.settings.columns_size = sav
