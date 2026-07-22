from itertools import chain
import html

from PySide6.QtGui import (QIcon, QPixmap, QBrush, QColor, QPainter)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QTreeWidgetItem)
from interpreter.utils.icons import icon_prefix
from api.testium import print_warn

# Maps item_name (from TestItemType.item_name) to visual config.
# Keys: icon (required), icon_on (optional 2nd state), expanded, unfoldable, no_breakpoint
_ITEM_CONFIG = {
    "unittest":             {"icon": "folder.png",        "icon_on": "folder-open.png", "expanded": True,  "no_breakpoint": True},
    "unittest step":        {"icon": "document.png",                                                        "no_breakpoint": True},
    "pytest":               {"icon": "pytest.png",                                       "expanded": True,  "no_breakpoint": True},
    "pytest step":          {"icon": "pytest.png",                                                          "no_breakpoint": True},
    "Console":              {"icon": "terminal.png",       "unfoldable": False},
    "Console action":       {"icon": "terminal.png"},
    "Cycle":                {"icon": "cycle.png",          "expanded": True},
    "python Function":      {"icon": "python.png"},
    "lua Function":         {"icon": "lua.png"},
    "Report":               {"icon": "report.png"},
    "git repository":       {"icon": "git.png"},
    "Runtime plot":         {"icon": "plot.png"},
    "Runtime plot action":  {"icon": "plot.png"},
    "Group":                {"icon": "group.png",          "expanded": True},
    "Image Dialog":         {"icon": "image.png"},
    "Message Dialog":       {"icon": "info.png"},
    "Let":                  {"icon": "let.png"},
    "Check value":          {"icon": "verif.png"},
    "Note Dialog":          {"icon": "note.png"},
    "Question Dialog":      {"icon": "question.png"},
    "Sleep":                {"icon": "sleep.png"},
    "References Dialog":    {"icon": "label.png"},
    "Value Dialog":         {"icon": "question.png"},
    "Choices Dialog":       {"icon": "label.png"},
    "Run tum":              {"icon": "run.png"},
    "JSON-RPC":             {"icon": "json.png",           "unfoldable": False},
    "JSON-RPC action":      {"icon": "json.png"},
    "Parallel":             {"icon": "parallel.png",        "expanded": True},
    "Parallel branch":      {"icon": "parallel_branch.png", "expanded": True},
}


def make_tree_item(parent, test_set_item, cols):
    """Factory: create a QTestTreeItem configured for the given test_set_item type."""
    item = QTestTreeItem(parent, test_set_item, cols)
    cfg = _ITEM_CONFIG.get(test_set_item["type"], {})
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
        self._failure_list = None
        self._no_breakpoint = False
        parent.addChild(self)
        self._has_failed = False
        self._display_pause = False
        self.icon_pause = _breakpoint_icon()
        self.icon_fake = QIcon()
        self.nfailure = 0
        self._timestamp = -1
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
        self.nfailure = 0
        self.setText(self._cols["failure"]["index"], str(self.nfailure))

    def clearStatusIcon(self):
        icon = QIcon()
        self.setIcon(self._cols["status"]["index"], icon)
        self._has_failed = False

    def setStatusIcon(self, success):
        icon = QIcon()
        if success:
            if self._has_failed:
                icon.addPixmap(QPixmap(icon_prefix() + "/success_orange.png"))
            else:
                icon.addPixmap(QPixmap(icon_prefix() + "/success.png"))
        else:
            icon.addPixmap(QPixmap(icon_prefix() + "/fail.png"))
            self._has_failed = True
            self.nfailure = self.nfailure + 1
            self.setText(self._cols["failure"]["index"], str(self.nfailure))

        self.setIcon(self._cols["status"]["index"], icon)

    def setBreakpointState(self, on):
        if self._no_breakpoint:
            return False
        self._display_pause = bool(on)
        if self._display_pause:
            self.setIcon(self._cols["pause"]["index"], self.icon_pause)
        else:
            self.setIcon(self._cols["pause"]["index"], self.icon_fake)
        return self._display_pause

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
        """Recompute name-column colours from flags: run (green) > search (amber) > none."""
        col = self._cols["name"]["index"]
        if self._is_highlighted:
            self.setBackground(col, QBrush(QColor(153, 255, 153)))
            self.setForeground(col, QBrush())
        elif self._is_search_match:
            self.setBackground(col, QBrush(QColor(255, 224, 130)))
            self.setForeground(col, QBrush(QColor(0, 0, 0)))
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
        """True if *needle* (lowercase) is in any enabled field (name/type/doc)."""
        if "name" in fields and needle in (self.name or "").lower():
            return True
        if "type" in fields and needle in (self.test_type or "").lower():
            return True
        if "doc" in fields and needle in str(self.doc or "").lower():
            return True
        return False

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

    def setTimestamp(self, val):
        if (self._timestamp < 0) and (val > 0):
            self._timestamp = val

    def timestamp(self):
        return self._timestamp
