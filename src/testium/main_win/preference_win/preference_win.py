from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QLineEdit
from PySide6.QtGui import QFont

from main_win.preference_win.preference_core_win import Ui_preferenceWindow
from main_win import file_dialog
from gui.preferences_presenter import PreferencesPresenter

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

        # Field list and store/restore logic in gui/preferences_presenter.py.
        s = prefs.settings
        self._widgets = {
            s.SettingsShowCheckboxes.name:  self.ui.checkBoxTest,
            s.SettingsShowTimeColumn.name:  self.ui.checkShowTime,
            s.SettingsLogPath.name:         self.ui.editDefaultLogPath,
            s.SettingsReportPath.name:      self.ui.editDefaultReportPath,
            s.SettingsDblClickEnabled.name: self.ui.checkDblClick,
            s.SettingsEditorCmd.name:       self.editEditorCmd,
            s.SettingsIconsTheme.name:      self.ui.choiceIconsTheme,
            s.SettingsLogFont.name:         self.ui.font_choice,
            s.SettingsLogFontSize.name:     self.ui.font_size,
            s.SettingsGitSupported.name:    self.ui.checkGitSupported,
            s.SettingsPythonPath.name:      self.ui.editPythonPath,
            s.SettingsLuaPath.name:         self.ui.editLuaPath,
        }
        self.presenter = PreferencesPresenter(self)
        self.restore_prefs()
        # Open sized to the content of the largest tab (a row is added in
        # code above, so the .ui geometry cannot know it); stays resizable.
        for sa in (self.ui.scrollArea, self.ui.scrollArea_2, self.ui.scrollArea_3):
            hint = sa.widget().sizeHint()
            sa.setMinimumHeight(hint.height() + 4)
            sa.setMinimumWidth(hint.width() + 4)
        self.adjustSize()

    # --- PreferencesView implementation (driven by gui/preferences_presenter.py)

    def field_value(self, key, ftype):
        return _FIELD[ftype][0](self._widgets[key.name])

    def set_field_value(self, key, ftype, value):
        _FIELD[ftype][1](self._widgets[key.name], value)

    # ----------------------------------------------------------------------

    def store_prefs(self):
        self.presenter.store()

    def restore_prefs(self):
        self.presenter.restore()

    def isChanged(self, setting):
        return self.presenter.is_changed(setting)

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
