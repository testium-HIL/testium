from collections import namedtuple

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QLineEdit
from PySide6.QtGui import QFont

from main_win.preference_win.preference_core_win import Ui_preferenceWindow
from main_win import file_dialog

import interpreter.utils.settings as prefs


def _set_font(w, v):
    f = QFont()
    f.fromString(v)
    w.setCurrentFont(f)


# Per-type widget <-> value bridge: (read from widget, write to widget).
_FIELD = {
    "bool":  (lambda w: w.isChecked(),              lambda w, v: w.setChecked(v)),
    "text":  (lambda w: w.text(),                   lambda w, v: w.setText(v)),
    "int":   (lambda w: int(w.value()),             lambda w, v: w.setValue(v)),
    "combo": (lambda w: int(w.currentIndex()),      lambda w, v: w.setCurrentIndex(v)),
    "font":  (lambda w: w.currentFont().toString(), _set_font),
}

Field = namedtuple("Field", "key type widget")


class PrefWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_preferenceWindow()
        self.ui.setupUi(self)
        self.setModal = True
        self.ui.buttonBox.accepted.connect(self.on_buttOKPressed)
        self.ui.buttonBox.rejected.connect(self.on_buttCancelPressed)
        self.finished.connect(self.on_finishedPressed)

        self.ui.butLogPath.triggered.connect(
            lambda: self._pick_dir(self.ui.editDefaultLogPath, "Select the default log directory"))
        self.ui.butReportPath.triggered.connect(
            lambda: self._pick_dir(self.ui.editDefaultReportPath, "Select the default report directory"))
        self.ui.butPythonPath.triggered.connect(
            lambda: self._pick_file(self.ui.editPythonPath, "Select the python interpreter"))
        self.ui.butLuaPath.triggered.connect(
            lambda: self._pick_file(self.ui.editLuaPath, "Select the lua interpreter"))

        # Editor command field, added in code (mirrors the F1 filter approach) so the
        # generated UI stays untouched. Sits with the double-click toggle it feeds.
        self.editEditorCmd = QLineEdit(self.ui.scrollAreaWidgetContents)
        self.editEditorCmd.setPlaceholderText("ex: code -g {file}:{line}")
        self.ui.formLayout.addRow(QLabel("Open log line in editor"), self.editEditorCmd)

        s = prefs.settings
        self.fields = [
            Field(s.SettingsHideDocPane,     "bool",  self.ui.checkDocPane),
            Field(s.SettingsHideLogPane,     "bool",  self.ui.checkLogPane),
            Field(s.SettingsShowCheckboxes,  "bool",  self.ui.checkBoxTest),
            Field(s.SettingsShowTimeColumn,  "bool",  self.ui.checkShowTime),
            Field(s.SettingsLogPath,         "text",  self.ui.editDefaultLogPath),
            Field(s.SettingsReportPath,      "text",  self.ui.editDefaultReportPath),
            Field(s.SettingsDblClickEnabled, "bool",  self.ui.checkDblClick),
            Field(s.SettingsEditorCmd,       "text",  self.editEditorCmd),
            Field(s.SettingsIconsTheme,      "combo", self.ui.choiceIconsTheme),
            Field(s.SettingsLogFont,         "font",  self.ui.font_choice),
            Field(s.SettingsLogFontSize,     "int",   self.ui.font_size),
            Field(s.SettingsGitSupported,    "bool",  self.ui.checkGitSupported),
            Field(s.SettingsPythonPath,      "text",  self.ui.editPythonPath),
            Field(s.SettingsLuaPath,         "text",  self.ui.editLuaPath),
        ]
        self._changed = set()
        self.restore_prefs()

    def store_prefs(self):
        self._changed = set()
        for f in self.fields:
            val = _FIELD[f.type][0](f.widget)
            if val != prefs.settings.value(f.key):
                prefs.settings.set_value(f.key, val)
                self._changed.add(f.key.name)
        prefs.settings.sync()

    def restore_prefs(self):
        for f in self.fields:
            _FIELD[f.type][1](f.widget, prefs.settings.value(f.key))

    def isChanged(self, setting):
        return setting.name in self._changed

    @Slot()
    def on_buttOKPressed(self):
        self.store_prefs()
        self.accept()

    @Slot()
    def on_buttCancelPressed(self):
        self.restore_prefs()
        self.reject()

    @Slot()
    def on_finishedPressed(self):
        self.restore_prefs()

    def _pick_dir(self, edit, caption):
        path = QFileDialog.getExistingDirectory(
            self, caption=caption, dir=edit.text(), options=file_dialog.options())
        if path:
            edit.setText(path)

    def _pick_file(self, edit, caption):
        path, _ = QFileDialog.getOpenFileName(
            self, caption=caption, dir=edit.text(), options=file_dialog.options())
        if path:
            edit.setText(path)
