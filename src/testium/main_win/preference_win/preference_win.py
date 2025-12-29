
from PySide6.QtCore import (Slot, Qt)
from PySide6.QtWidgets import (QDialog, QFileDialog)
from PySide6.QtGui import (QFont)

from main_win.preference_win.preference_core_win import Ui_preferenceWindow

import interpreter.utils.settings as prefs

class PrefWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_preferenceWindow()
        self.ui.setupUi(self)
        self.setModal = (True)
        self.ui.buttonBox.accepted.connect(self.on_buttOKPressed)
        self.ui.buttonBox.rejected.connect(self.on_buttCancelPressed)
        self.finished.connect(self.on_finishedPressed)
        self.ui.butLogPath.triggered.connect(self.on_butLogPath_pressed)
        self.ui.butReportPath.triggered.connect(self.on_butReportPath_pressed)
        self.elements = {
            prefs.settings.SettingsHideDocPane: {
                'type': 'bool',
                'widget': self.ui.checkDocPane,
                'value': prefs.settings.hide_doc_pane,
                'default': False,
                'changed': False,
            },
            prefs.settings.SettingsHideLogPane: {
                'type':  'bool',
                'widget': self.ui.checkLogPane,
                'value': prefs.settings.hide_log_pane,
                'default': False,
                'changed': False,
            },
            prefs.settings.SettingsShowCheckboxes: {
                'type':  'bool',
                'widget': self.ui.checkBoxTest,
                'value': prefs.settings.show_checkboxes,
                'default': False,
                'changed': False,
            },
            prefs.settings.SettingsShowTimeColumn: {
                'type':  'bool',
                'widget': self.ui.checkShowTime,
                'value': prefs.settings.show_time_column,
                'default': False,
                'changed': False,
            },
            prefs.settings.SettingsLogPath: {
                'type':  'text',
                'widget': self.ui.editDefaultLogPath,
                'value': prefs.settings.log_path,
                'default': '$(test_directory)',
                'changed': False,
            },
            prefs.settings.SettingsReportPath: {
                'type' : 'text',
                'widget': self.ui.editDefaultReportPath,
                'value': prefs.settings.report_path,
                'default': '$(test_directory)',
                'changed': False,
            },
            prefs.settings.SettingsDblClickEnabled: {
                'type' : 'bool',
                'widget': self.ui.checkDblClick,
                'value': prefs.settings.dbl_click_enabled,
                'default': False,
                'changed': False,
            },
            prefs.settings.SettingsIconsTheme: {
                'type' : 'combo',
                'widget': self.ui.choiceIconsTheme,
                'value': prefs.settings.icons_theme,
                'default': 0,
                'changed': False,
            },
            prefs.settings.SettingsLogFont: {
                'type' : 'font',
                'widget': self.ui.font_choice,
                'value': prefs.settings.log_font,
                'default': 'Monospace',
                'changed': False,
            },
            prefs.settings.SettingsLogFontSize: {
                'type' : 'int',
                'widget': self.ui.font_size,
                'value': prefs.settings.log_font_size,
                'default': 8,
                'changed': False,
            },
            prefs.settings.SettingsGitSupported: {
                'type' : 'bool',
                'widget': self.ui.checkGitSupported,
                'value': prefs.settings.git_supported,
                'default': True,
                'changed': False,
            }
        }

        self.restore_prefs()

    def store_prefs(self):
        for k, v in self.elements.items():
            self.elements[k]['changed'] = False
            if v['type'] == 'bool':
                val = v['widget'].isChecked()
                if self.elements[k]['value'] != val:
                    self.elements[k]['value'] = val
                    self.elements[k]['changed'] = True

            if v['type'] == 'text':
                val = v['widget'].text()
                if self.elements[k]['value'] != val:
                    self.elements[k]['value'] = val
                    self.elements[k]['changed'] = True

            if v['type'] == 'font':
                val = v['widget'].currentFont().toString()
                if self.elements[k]['value'] != val:
                    self.elements[k]['value'] = val
                    self.elements[k]['changed'] = True

            if v['type'] == 'int':
                val = int(v['widget'].value())
                if self.elements[k]['value'] != val:
                    self.elements[k]['value'] = val
                    self.elements[k]['changed'] = True

            if v['type'] == 'combo':
                val = int(v['widget'].currentIndex())
                if self.elements[k]['value'] != val:
                    self.elements[k]['value'] = val
                    self.elements[k]['changed'] = True

            if self.elements[k]['changed']:
                prefs.settings.set_value(k, v['value'])

        prefs.settings.sync()

    def restore_prefs(self):
        for k, v in self.elements.items():
            v['value'] = prefs.settings.value(k, v['default'])
            if v['type'] == 'bool':
                v['widget'].setChecked(v['value'])
            elif v['type'] == 'text':
                v['widget'].setText(self.elements[k]['value'])
            elif v['type'] == 'font':
                f = QFont()
                f.fromString(self.elements[k]['value'])
                v['widget'].setCurrentFont(f)
            elif v['type'] == 'int':
                v['widget'].setValue(self.elements[k]['value'])
            elif v['type'] == 'combo':
                v['widget'].setCurrentIndex(self.elements[k]['value'])

    def isChanged(self, setting):
        return self.elements[setting]['changed']

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

    @Slot()
    def on_butReportPath_pressed(self):
        path = QFileDialog.getExistingDirectory(self, "Select the default report directory",
                                                  self.ui.editDefaultReportPath.text())
        if path:
            self.ui.editDefaultReportPath.setText(path)

    @Slot()
    def on_butLogPath_pressed(self):
        path = QFileDialog.getExistingDirectory(self, "Select the default log directory",
                                                  self.ui.editDefaultLogPath.text())
        if path:
            self.ui.editDefaultLogPath.setText(path)
