from itertools import chain
import html

from PySide6.QtGui import (QIcon, QPixmap, QBrush, QColor, QPainter)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QTreeWidgetItem)
from interpreter.utils.icons import icon_prefix
from api.testium import print_warn
from gui import tree_view_model


def make_tree_item(parent, test_set_item, cols):
    """Factory: create a QTestTreeItem configured for the given test_set_item type."""
    item = QTestTreeItem(parent, test_set_item, cols)
    cfg = tree_view_model.ITEM_CONFIG.get(test_set_item["type"], {})
    if cfg.get("unfoldable") is False:
        item.recursive_unfoldable = False
    if cfg.get("expanded"):
        item.setExpanded(True)
    if cfg.get("no_breakpoint"):
        item._no_breakpoint = True
    icon = cfg.get("icon", "")
    if icon:
        icon_on = cfg.get("icon_on", "")
        item.setRowIcon(
            icon_prefix() + "/" + icon,
            icon_prefix() + "/" + icon_on if icon_on else "",
        )
    return item


def __iter__QTreeWidgetItem(self):
    for item in chain(*map(iter, self.children())):
        yield item
    yield self


def childrenQTreeWidgetItem(self):
    return [self.child(i) for i in range(self.childCount())]


QTreeWidgetItem.name = ""
QTreeWidgetItem.id = 0
QTreeWidgetItem.__iter__ = __iter__QTreeWidgetItem
QTreeWidgetItem.children = childrenQTreeWidgetItem


_breakpoint_icon_cache = None


def _breakpoint_icon():
    """Big red dot (universal breakpoint marker), drawn once — same in every
    icon theme, no PNG variants needed."""
    global _breakpoint_icon_cache
    if _breakpoint_icon_cache is None:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(220, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(12, 12, 40, 40)
        painter.end()
        _breakpoint_icon_cache = QIcon(pixmap)
    return _breakpoint_icon_cache


_conditional_bp_icon_cache = None


def _conditional_bp_icon():
    """Hollow red ring: breakpoint with a condition."""
    global _conditional_bp_icon_cache
    if _conditional_bp_icon_cache is None:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = painter.pen()
        pen.setColor(QColor(220, 0, 0))
        pen.setWidth(10)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(12, 12, 40, 40)
        painter.end()
        _conditional_bp_icon_cache = QIcon(pixmap)
    return _conditional_bp_icon_cache


_attach_icon_cache = {}


def _attach_icon(with_breakpoint):
    """Blue dot marking a py_func item waiting for a debugger; drawn beside
    the red dot when the item also has a breakpoint."""
    icon = _attach_icon_cache.get(with_breakpoint)
    if icon is None:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        if with_breakpoint:
            painter.setBrush(QColor(220, 0, 0))
            painter.drawEllipse(2, 16, 32, 32)
            painter.setBrush(QColor(0, 90, 220))
            painter.drawEllipse(30, 16, 32, 32)
        else:
            painter.setBrush(QColor(0, 90, 220))
            painter.drawEllipse(12, 12, 40, 40)
        painter.end()
        icon = QIcon(pixmap)
        _attach_icon_cache[with_breakpoint] = icon
    return icon


def pretty_print_html(text):
    if text.strip(" \t\n") == "":
        return ""

    text = html.escape(text)  # échappe <, >, etc.
    return f"<pre style='font-family: monospace; font-size: 8pt'>{text}</pre>"


class QTestTreeItem(QTreeWidgetItem):
    def __init__(self, parent, test_set_item, cols):
        index = parent.childCount()
        super().__init__()
        self.recursive_unfoldable = True
        parent.insertChild(index, self)
        self.name = test_set_item["name"]
        self.doc = test_set_item["doc"]
        self.content = pretty_print_html(test_set_item["content"])
        self.seq_filename = test_set_item["seq_filename"]
        self._cols = cols
        self.setText(self._cols["name"]["index"], self.name)
        self.id = test_set_item["id"]
        self.setType(test_set_item)
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
        self.setCheckState(self._cols["name"]["index"], Qt.Checked)
        self._is_highlighted = False
        self._is_search_match = False
        self._no_breakpoint = False
        parent.addChild(self)
        self._display_pause = False
        self._bp_condition = None
        self._debug_attach = False
        self.icon_pause = _breakpoint_icon()
        self.icon_fake = QIcon()
        self._is_skipped = False
        tool_tip = (
            None
            if self.doc is None
            else "<b>" + self.name + "</b><br>" + str(self.doc)
        )
        # tool_tip = (
        #     tool_tip
        #     if self.content == ""
        #     else self.content if tool_tip is None else tool_tip + "<br>" + "_"*10 + self.content
        # )
        self.setToolTip(self._cols["name"]["index"], tool_tip)
        self.setToolTip(self._cols["type"]["index"], tool_tip)

    def setType(self, test_set_item):
        # if hasattr(self, '_custom_type'):
        #     self.setText(self._cols['type']['index'], self._custom_type)
        # else:
        self.test_type = test_set_item["type"]
        self.setText(self._cols["type"]["index"], self.test_type)

    def clearStatus(self):
        self.clearStatusIcon()
        self.setText(self._cols["failure"]["index"], "0")

    def clearStatusIcon(self):
        self.setIcon(self._cols["status"]["index"], QIcon())

    _STATUS_PNG = {
        "success": "success.png",
        "success_after_fail": "success_orange.png",
        "fail": "fail.png",
    }

    def setStatusIcon(self, kind):
        """kind: a StatusUpdate.icon value from gui/status_presenter.py."""
        icon = QIcon()
        icon.addPixmap(QPixmap(icon_prefix() + "/" + self._STATUS_PNG[kind]))
        self.setIcon(self._cols["status"]["index"], icon)

    def setBreakpointState(self, on, condition=None):
        if self._no_breakpoint:
            return False
        self._display_pause = bool(on)
        self._bp_condition = condition if self._display_pause else None
        tip = None
        if self._bp_condition:
            tip = "Breakpoint condition: " + self._bp_condition
        self.setToolTip(self._cols["pause"]["index"], tip)
        self._refresh_gutter()
        return self._display_pause

    def setDebugAttachState(self, on):
        self._debug_attach = bool(on)
        self._refresh_gutter()
        return self._debug_attach

    def isDebugAttach(self):
        return getattr(self, "_debug_attach", False)

    def _refresh_gutter(self):
        col = self._cols["pause"]["index"]
        kind = tree_view_model.gutter_icon(
            self.isDebugAttach(), self._display_pause, self._bp_condition)
        if kind == "attach_bp":
            self.setIcon(col, _attach_icon(True))
        elif kind == "attach":
            self.setIcon(col, _attach_icon(False))
        elif kind == "bp_conditional":
            self.setIcon(col, _conditional_bp_icon())
        elif kind == "bp":
            self.setIcon(col, self.icon_pause)
        else:
            self.setIcon(col, self.icon_fake)

    def setBreakpoint(self):
        return self.setBreakpointState(not self._display_pause)

    def setBreakpointIfCol(self, column):
        ret = False
        if column == self._cols["pause"]["index"]:
            ret = True
            self.setBreakpoint()
        return ret

    def isBreakpoint(self):
        return self._display_pause

    def _refresh_highlight(self):
        """Recompute name-column colours; precedence and palette in
        gui/tree_view_model.py."""
        col = self._cols["name"]["index"]
        style = tree_view_model.highlight_style(
            self._is_highlighted, self._is_search_match)
        if style == "run":
            self.setBackground(col, QBrush(QColor(tree_view_model.RUN_BG)))
            self.setForeground(col, QBrush())
        elif style == "search":
            self.setBackground(col, QBrush(QColor(tree_view_model.SEARCH_BG)))
            self.setForeground(col, QBrush(QColor(tree_view_model.SEARCH_FG)))
        else:
            self.setBackground(col, QBrush())
            self.setForeground(col, QBrush())

    def setHighlighted(self):
        if not self._is_highlighted:
            self._is_highlighted = True
            self._refresh_highlight()

    def resetHighlighted(self):
        if self._is_highlighted:
            self._is_highlighted = False
            self._refresh_highlight()

    def matches_search(self, needle, fields):
        return tree_view_model.matches_search(
            needle, fields, self.name, self.test_type, self.doc)

    def setSearchMatch(self, on):
        """Search highlight (amber bg + black text), readable in any theme."""
        if on != self._is_search_match:
            self._is_search_match = on
            self._refresh_highlight()

    def setRowIcon(self, resource_off, resource_on=""):

        icon = QIcon()
        icon.addPixmap(QPixmap(resource_off))
        if resource_on != "":
            icon.addPixmap(QPixmap(resource_on), QIcon.Normal, QIcon.On)
        self.setIcon(self._cols["name"]["index"], icon)
