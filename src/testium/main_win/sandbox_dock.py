# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Script sandbox dock: run Python, Lua or Tcl snippets against the
loaded test. Display only; the logic lives in gui/sandbox_presenter.py."""

import os

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtGui import (QColor, QFont, QSyntaxHighlighter,
                           QTextCharFormat, QTextCursor)
from PySide6.QtWidgets import (QComboBox, QCompleter, QDockWidget,
                               QFileDialog, QHBoxLayout, QLabel, QMenu,
                               QMessageBox, QPlainTextEdit, QPushButton,
                               QSplitter, QToolButton, QVBoxLayout, QWidget)

from gui import sandbox_syntax as syntax
from gui.sandbox_presenter import SandboxPresenter
from main_win import file_dialog

import interpreter.utils.settings as prefs

_LABELS = (("Python", "python"), ("Lua", "lua"), ("Tcl", "tcl"))

# kind -> (color on a light background, color on a dark background, bold)
_SYNTAX_COLORS = {
    "keyword": ("#00599c", "#6cb6ff", True),
    "api": ("#7a3e9d", "#d2a8ff", True),
    "string": ("#1a7f37", "#7ee787", False),
    "comment": ("#6e7781", "#8b949e", False),
    "number": ("#b35900", "#ffa657", False),
    "variable": ("#9a6700", "#e3b341", False),
}
_OUTPUT_COLORS = {
    "result": ("#00599c", "#6cb6ff"),
    "error": ("#b71c1c", "#ff7b72"),
    "info": ("#6e7781", "#8b949e"),
}


def _is_dark(widget):
    return widget.palette().base().color().lightness() < 128


class _Highlighter(QSyntaxHighlighter):
    def __init__(self, document, dark):
        super().__init__(document)
        self._lang = "python"
        self._formats = {}
        for kind, (light, dark_color, bold) in _SYNTAX_COLORS.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(dark_color if dark else light))
            if bold:
                fmt.setFontWeight(QFont.Bold)
            self._formats[kind] = fmt

    def set_language(self, lang):
        self._lang = lang
        self.rehighlight()

    def highlightBlock(self, text):
        state = self.previousBlockState()
        spans, state = syntax.highlight_line(
            self._lang, text, state if state > 0 else syntax.NORMAL)
        for start, length, kind in spans:
            self.setFormat(start, length, self._formats[kind])
        self.setCurrentBlockState(state)


class _CodeEdit(QPlainTextEdit):
    """Ctrl+Enter runs, Ctrl+Space completes, Tab inserts four spaces."""

    def __init__(self, on_run, on_complete, parent=None):
        super().__init__(parent)
        self._on_run = on_run
        self._on_complete = on_complete
        self._prefix = ""
        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        self._completer.setModel(QStringListModel(self))
        self._completer.activated[str].connect(self._insert_completion)

    def before_cursor(self):
        cursor = self.textCursor()
        return cursor.block().text()[:cursor.positionInBlock()]

    def show_completions(self, prefix, names):
        popup = self._completer.popup()
        if not names:
            popup.hide()
            return
        self._prefix = prefix
        self._completer.model().setStringList(names)
        self._completer.setCompletionPrefix("")
        rect = self.cursorRect()
        rect.setWidth(popup.sizeHintForColumn(0)
                      + popup.verticalScrollBar().sizeHint().width() + 8)
        self._completer.complete(rect)
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))

    def _insert_completion(self, name):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Left,
                            QTextCursor.MoveMode.KeepAnchor,
                            len(self._prefix))
        cursor.insertText(name)
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        key = event.key()
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        popup = self._completer.popup()
        if popup.isVisible():
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab,
                       Qt.Key.Key_Escape, Qt.Key.Key_Backtab):
                # Handled by the completer.
                event.ignore()
                return
        if ctrl and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_run()
            return
        if ctrl and key == Qt.Key.Key_Space:
            self._on_complete()
            return
        if key == Qt.Key.Key_Tab and not self.textCursor().hasSelection():
            self.insertPlainText("    ")
            return
        super().keyPressEvent(event)
        if popup.isVisible() or event.text() in (".", ":"):
            text = self.before_cursor()
            if popup.isVisible() or text.endswith((".", "::")):
                self._on_complete()


class SandboxDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Sandbox", parent)
        self.setObjectName("sandboxDock")
        self._service = None
        self._syncing = False

        mono = QFont("Monospace")
        mono.setStyleHint(QFont.StyleHint.TypeWriter)
        mono.setPointSizeF(max(7.0, self.font().pointSizeF() - 1))

        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.lang_combo = QComboBox()
        for label, lang in _LABELS:
            self.lang_combo.addItem(label, lang)
        self.lang_combo.setToolTip("Script language")
        self.session_combo = _SessionCombo(self._on_sessions_popup)
        self.session_combo.setMinimumContentsLength(12)
        self.session_combo.setToolTip(
            "Sandbox: process of this panel.\n"
            "Other entries: active context_id of the paused run.")
        self.run_button = QPushButton("Run")
        self.run_button.setToolTip("Run the script (Ctrl+Enter)")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setToolTip("Kill the process of the running script")
        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Restart the process of the session")
        self.file_button = QToolButton()
        self.file_button.setText("File")
        self.file_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup)
        self._file_menu = QMenu(self.file_button)
        self._file_menu.aboutToShow.connect(self._fill_file_menu)
        self.file_button.setMenu(self._file_menu)
        self.file_label = QLabel()
        self.clear_button = QToolButton()
        self.clear_button.setText("Clear")
        self.clear_button.setToolTip("Clear the output")

        row = QHBoxLayout()
        row.addWidget(self.lang_combo)
        row.addWidget(self.session_combo)
        row.addWidget(self.run_button)
        row.addWidget(self.stop_button)
        row.addWidget(self.reset_button)
        row.addWidget(self.file_button)
        row.addWidget(self.file_label, 1)
        row.addWidget(self.clear_button)
        layout.addLayout(row)

        self.code_edit = _CodeEdit(self._on_run, self._on_complete)
        self.code_edit.setFont(mono)
        self.code_edit.setPlaceholderText(
            "Script  (Ctrl+Enter runs, Ctrl+Space completes)")
        self.code_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._highlighter = _Highlighter(self.code_edit.document(),
                                         _is_dark(self.code_edit))
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(mono)
        self.output.setPlaceholderText("Output")
        self.output.setMaximumBlockCount(5000)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.code_edit)
        splitter.addWidget(self.output)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)
        self.setWidget(body)

        self.presenter = SandboxPresenter(
            self, lambda: self._service,
            load_state=lambda: prefs.settings.sandbox_state,
            save_state=self._save_state)

        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        self.session_combo.currentTextChanged.connect(self._on_session_changed)
        self.run_button.clicked.connect(self._on_run)
        self.stop_button.clicked.connect(self.presenter.stop)
        self.reset_button.clicked.connect(self.presenter.reset)
        self.clear_button.clicked.connect(self.output.clear)
        self.code_edit.textChanged.connect(self._update_file_label)
        self.presenter.start()

    # ----- wiring from the main window -----

    def set_service(self, service):
        self._service = service
        self.presenter.set_loaded(service is not None)

    def on_sandbox_event(self, message):
        self.presenter.on_event(message)

    def on_status(self, message):
        """Item status of the run: the context list changes on a pause."""
        if message.get("status") == "paused":
            self.presenter.refresh_sessions()

    def on_run_finished(self):
        self.presenter.refresh_sessions()

    def send_item(self, item_id):
        if self.presenter.send_item(item_id):
            self.show()
            self.raise_()
            self.code_edit.setFocus()

    def persist(self):
        self.presenter.persist()

    @staticmethod
    def _save_state(text):
        prefs.settings.sandbox_state = text
        prefs.settings.sync()

    # ----- SandboxView -----

    def code(self):
        return self.code_edit.toPlainText()

    def set_code(self, text):
        self.code_edit.setPlainText(text)

    def set_language(self, lang):
        self._syncing = True
        self.lang_combo.setCurrentIndex(self.lang_combo.findData(lang))
        self._syncing = False
        self._highlighter.set_language(lang)

    def set_sessions(self, names, current):
        self._syncing = True
        self.session_combo.clear()
        self.session_combo.addItems(names)
        self.session_combo.setCurrentText(current)
        self._syncing = False

    def set_sandbox_state(self, enabled, running):
        self.code_edit.setEnabled(enabled)
        self.lang_combo.setEnabled(enabled and not running)
        self.session_combo.setEnabled(enabled and not running)
        self.run_button.setEnabled(enabled and not running)
        self.stop_button.setEnabled(enabled and running)
        self.reset_button.setEnabled(enabled and not running)
        self.file_button.setEnabled(enabled and not running)

    def set_file_label(self, name, path):
        self._file_name = name
        self.file_label.setToolTip(path)
        self._update_file_label()

    def _update_file_label(self):
        name = getattr(self, "_file_name", "")
        if name and self.presenter.is_modified():
            name += " *"
        self.file_label.setText(name)

    def append_output(self, text, kind):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        colors = _OUTPUT_COLORS.get(kind)
        if colors:
            fmt.setForeground(
                QColor(colors[1] if _is_dark(self.output) else colors[0]))
        else:
            fmt.setForeground(self.output.palette().text())
        cursor.insertText(text, fmt)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def confirm(self, question):
        return QMessageBox.question(
            self, "Sandbox", question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def ask_open_path(self, start_dir):
        path, _ = QFileDialog.getOpenFileName(
            self, caption="Open a script", dir=start_dir,
            filter="Scripts (*.py *.lua *.tcl);;All files (*)",
            options=file_dialog.options())
        return path

    def ask_save_path(self, start, extension):
        path, _ = QFileDialog.getSaveFileName(
            self, caption="Save the script", dir=start,
            filter=f"Scripts (*{extension});;All files (*)",
            options=file_dialog.options())
        return path

    def show_completions(self, prefix, names):
        self.code_edit.show_completions(prefix, names)

    # ----- view events -----

    def _on_run(self):
        self.presenter.run()

    def _on_complete(self):
        self.presenter.complete(self.code_edit.before_cursor())

    def _on_lang_changed(self, index):
        if not self._syncing:
            self.presenter.on_language_changed(self.lang_combo.itemData(index))

    def _on_session_changed(self, name):
        if not self._syncing and name:
            self.presenter.on_session_changed(name)

    def _on_sessions_popup(self):
        self.presenter.refresh_sessions()

    def _fill_file_menu(self):
        menu = self._file_menu
        menu.clear()
        menu.addAction("Open...", self.presenter.open_file)
        scripts = self.presenter.test_scripts()
        sub = menu.addMenu("Test scripts")
        sub.setEnabled(bool(scripts))
        for _lang, path in scripts:
            action = sub.addAction(os.path.basename(path))
            action.setToolTip(path)
            action.triggered.connect(
                lambda _checked=False, p=path: self.presenter.open_file(p))
        sub.setToolTipsVisible(True)
        menu.addSeparator()
        menu.addAction("Save", self.presenter.save)
        menu.addAction("Save as...", self.presenter.save_as)
        menu.addAction("Detach from file", self.presenter.close_file)


class _SessionCombo(QComboBox):
    """Refreshes its entries when the list opens."""

    def __init__(self, on_popup, parent=None):
        super().__init__(parent)
        self._on_popup = on_popup

    def showPopup(self):
        self._on_popup()
        super().showPopup()
