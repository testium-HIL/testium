import sys
import os
import webbrowser
from multiprocessing import Queue
from threading import Thread
import shutil

# Qt
from PySide6 import QtGui
from PySide6.QtGui import QAction, QShortcut, QIcon, QPixmap, QTextCursor, QDesktopServices, QTextCursor
from PySide6.QtCore import Slot, QUrl, Qt, QTimer

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QFileDialog,
    QSizePolicy,
)

ourPath = os.path.dirname(__file__)
sys.path.append(os.path.join(ourPath, "resources"))

# user interfaces
from main_win.testium_core_win import Ui_MainWindow
from main_win.text_log import QTextLog
from main_win.about_win.about_win import Ui_About
from main_win.preference_win.preference_win import PrefWindow
from main_win.f1_win.d_f1_win import DialogF1
from main_win.test_tree import QTestTree

from main_win.test_run.thread_output import ThreadTestOutput
from lib.string_queue import StringQueue
from interpreter.process import TestProcess
from interpreter.utils.test_ctrl import TestSetController
from interpreter.utils.icons import icon_prefix

from main_win.test_run.outlog import OutLog
from main_win.test_run.test_run import ThreadTestStatus
import interpreter.utils.settings as prefs
from lib.stdout_redirect import stdio_redir
import libs.testium as tm
from interpreter.utils.version import get_testium_version
from interpreter.utils.test_init import (
    env_init,
    locate_report_file,
)
from lib.tum_except import ETUMFileError, ETUMRuntimeError
from main_win.test_controller_service import TestControllerService
from main_win.test_runner import TestRunner, TestState
from main_win.test_file_manager import TestFileManager


class MainWindow(QMainWindow, Ui_MainWindow):
    MaxRecentFiles = 5

    def __init__(
        self,
        test_file=None,
        config_files="",
        runandclose=False,
        log_file="",
        defines={},
        report="",
        report_type="",
        report_pattern=[],
        debug=False,
    ):
        super().__init__()
        self.setupUi(self)
        self.textLog = self.create_text_log(self.frame1)
        self.verticalLayout_2.addWidget(self.textLog)

        self._setup_icons()

        self.runandclose = runandclose
        self.mainWindowTitle = self.windowTitle()
        self.defines = defines
        self.logFileName = log_file
        self.reportFileName = report
        self.report_type = report_type
        self.report_pattern = report_pattern
        self.config_files = config_files
        self.recentFileActs = []
        self.debug = debug
        self.test_proc = None
        self.ts_controller = None
        self.test_service = None
        self.threadTestStatus = None
        self._signals_connected = False
        self.run_exit_code = -1  # -1 = test not yet completed

        self.timer = QTimer()
        self.timer.setSingleShot(False)
        self.timer.stop()
        self.timer.setInterval(100)

        self.timerBlink = QTimer()
        self.timerBlink.setSingleShot(False)
        self.timerBlink.stop()
        self.timerBlink.setInterval(1000)
        self.timerPause = QTimer()
        self.timerPause.setSingleShot(False)
        self.timerPause.stop()
        self.timerPause.setInterval(500)
        self.timerPause.state = False
        self.iconBlinkGreen = QIcon()
        self.iconBlinkGreen.addPixmap(QPixmap(icon_prefix() + "/green.png"))
        self.iconBlinkRed = QIcon()
        self.iconBlinkRed.addPixmap(QPixmap(icon_prefix() + "/red.png"))
        self.iconBlinkGray = QIcon()
        self.iconBlinkGray.addPixmap(QPixmap(icon_prefix() + "/gray.png"))

        self.threads_queue = Queue()
        self.status_queue = Queue()

        # Managers
        self.runner = TestRunner(self)
        self.file_manager = TestFileManager(self)

        self.runner.set_blink_green()

        env_init()

        # Persistence
        self.pref_win = PrefWindow(self)

        lastLog = prefs.settings.log_file
        if self.logFileName == "":
            self.editLogFilePath.setText(lastLog)
            self.logFileName = lastLog
            if prefs.settings.log_file_saved:
                self.buttLogFileSaved.setChecked(True)
        else:
            if not os.path.isabs(self.logFileName):
                self.logFileName = os.path.join(os.getcwd(), self.logFileName)
            self.buttLogFileSaved.setChecked(True)
        self.editLogFilePath.setText(self.logFileName)

        geo_settings = prefs.settings.value(
            prefs.SettingsItem("geometry", bytearray), bytearray()
        )
        if geo_settings:
            self.restoreGeometry(geo_settings)

        state_settings = prefs.settings.value(
            prefs.SettingsItem("state", bytearray), bytearray()
        )
        if state_settings:
            self.restoreState(state_settings)

        self.actionStart_test.setDisabled(True)
        self.actionShow_Results.setDisabled(True)
        self.actionSave_report.setDisabled(True)

        self.create_tree()

        self.shorcut_stop = QShortcut(
            Qt.Key_Space,
            self.treeTests,
            context=Qt.WidgetShortcut,
            activated=self.on_spacePressed,
        )
        self.shorcut_f1 = QShortcut(
            Qt.Key_F1,
            self.treeTests,
            context=Qt.WidgetShortcut,
            activated=self.on_F1Pressed,
        )

        self.actionRefresh_test.setDisabled(True)

        # Signal connections
        self.buttLogFilePath.pressed.connect(self.on_buttLogFilePath_clicked)
        self.buttClearLog.pressed.connect(self.on_buttClearLog_clicked)
        self.buttGoBottom.pressed.connect(self.on_buttGoBottom_clicked)
        self.editLogFilePath.editingFinished.connect(self.on_configLog_changed)
        self.buttLogFileSaved.toggled.connect(self.on_configLogSaved_changed)
        self.buttLogFileNone.toggled.connect(self.on_configLogNone_changed)
        self.timer.timeout.connect(self.runner.on_timer_event)
        self.timerBlink.timeout.connect(self.runner.on_timer_blink)
        self.timerBlink.timeout.connect(self.runner.on_timer_count)
        self.timerPause.timeout.connect(self.runner.on_timer_pause)
        self.treeTests.itemSelectionChanged.connect(self.on_testSelectionChanged)
        if prefs.settings.dbl_click_enabled:
            self.treeTests.setExpandsOnDoubleClick(False)
            self.treeTests.itemDoubleClicked.connect(self.on_testItemDblClicked)
        else:
            self.treeTests.setExpandsOnDoubleClick(True)
        QApplication.instance().lastWindowClosed.connect(self.on_exiting)

        self.prefs_apply_font()
        self.prefs_apply_font_size()

        # Recent files menu
        for i in range(MainWindow.MaxRecentFiles):
            self.recentFileActs.append(
                QAction(self, visible=False, triggered=self.file_manager.on_open_recent_file)
            )
        self.separatorAct = self.menuFile.addSeparator()
        for i in range(MainWindow.MaxRecentFiles):
            self.menuFile.addAction(self.recentFileActs[i])
        self.file_manager.update_recent_file_actions()

        # Secondary windows
        self.d_about_win = QDialog()
        self.about_win = Ui_About()
        self.about_win.setupUi(self.d_about_win)
        self.about_win.labelVersion.setText("testium - " + get_testium_version())
        self.about_win.labelCesUnitVersion.setText("")
        self.d_about_win.setModal(True)

        self.d_f1_win = DialogF1(self)

        self.stream = StringQueue()
        stdio_redir.redirect(self.stream)
        self.threadOutput = ThreadTestOutput(self.stream, self.threads_queue)
        self.threadOutput.start()

        self.out_log = OutLog()
        self.out_log.logToBeAppended.connect(self.on_logToBeAppended)
        self.redirectStdToTextLog(self.out_log)
        self.testFile = test_file

        self.threadTestStatus = ThreadTestStatus(self.status_queue, debug=self.debug)
        self.threadTestStatus.start()

        self.update_from_prefs()

        self.reportFileName = locate_report_file(self.reportFileName)

        last_files = prefs.settings.recent_files
        ret = False
        if test_file != "":
            if not os.path.isabs(test_file):
                test_file = os.path.join(os.getcwd(), test_file)
            if os.path.isfile(test_file):
                ret = self.file_manager.load(test_file)
        elif (len(last_files) > 0) and os.path.isfile(last_files[0]):
            ret = self.file_manager.load(last_files[0])

        if ret:
            self.file_loaded_at_startup()

        self.threadTestStatus.testSetIsFinished.connect(self.runner.on_run_finished)
        self.threadTestStatus.statusToBeUpdated.connect(self.treeTests.updateStatus)
        self.threadTestStatus.gdUpdated.connect(self.d_f1_win.gd_var_updated)
        self.threadTestStatus.gdDeleted.connect(self.d_f1_win.gd_var_deleted)
        self.reconnect_signals()

        if runandclose:
            self.on_actionStart_test_triggered()

    def _setup_icons(self):
        icons = {
            self.buttClearLog:          "edit-clear",
            self.buttGoBottom:          "go-bottom",
            self.actionOpenTest:        "document-open",
            self.actionSave_report:     "document-save",
            self.actionStart_test:      "start",
            self.actionStop_test:       "stop",
            self.actionAbout_testium:   "about",
            self.actionExit:            "exit",
            self.actionRefresh_test:    "view-refresh",
            self.actionShow_Results:    "results",
            self.actionHelp:            "help",
            self.actionPreferences:     "settings",
            self.actionTestInformation: "info",
        }
        for widget, name in icons.items():
            icon = QtGui.QIcon()
            icon.addPixmap(
                QtGui.QPixmap(icon_prefix() + f"/{name}.png"),
                QtGui.QIcon.Normal,
                QtGui.QIcon.Off,
            )
            widget.setIcon(icon)

    def create_text_log(self, parent):
        return QTextLog(parent)

    def create_tree(self):
        self.treeTests = QTestTree(self.widget)
        self.treeTests.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeTests.sizePolicy().hasHeightForWidth())
        self.treeTests.setSizePolicy(sizePolicy)
        self.treeTests.breakpoint.connect(self.on_breakpoint)
        self.verticalLayout.addWidget(self.treeTests)

    def remove_tree(self):
        self.verticalLayout.removeWidget(self.treeTests)
        del self.treeTests
        self.treeTests = None

    def file_loaded_at_startup(self):
        modeSlider_value = prefs.settings.show_checkboxes
        if modeSlider_value:
            checkList = prefs.settings.value(prefs.SettingsItem("checkList", list), [])
            if checkList is not None:
                if len(checkList) == self.treeTests.getItemCount():
                    self.treeTests.restoreCheckList(checkList, self.test_service)
                else:
                    tm.print_info(
                        "The number of tests has changed. Test box states are not restored."
                    )
        foldList = prefs.settings.value(prefs.SettingsItem("foldList", list), [])
        if foldList:
            if len(foldList) == self.treeTests.getItemCount():
                self.checkFold.setCheckState(Qt.PartiallyChecked)
                self.treeTests.restoreFoldList(foldList)

    def disconnect_signals(self):
        if self._signals_connected:
            self.checkSelect.stateChanged.disconnect()
            self.treeTests.itemChanged.disconnect()
            self.checkFold.stateChanged.disconnect()
            self.treeTests.itemCollapsed.disconnect()
            self.treeTests.itemExpanded.disconnect()
            self._signals_connected = False

    def reconnect_signals(self):
        if not self._signals_connected:
            self.checkSelect.stateChanged.connect(self.on_selectDeselectAll)
            self.treeTests.itemChanged.connect(self.on_testChecked)
            self.checkFold.stateChanged.connect(self.on_checkFoldChanged)
            self.treeTests.itemCollapsed.connect(self.on_itemFoldChanged)
            self.treeTests.itemExpanded.connect(self.on_itemFoldChanged)
            self._signals_connected = True

    def prefs_apply_font(self):
        f = self.textLog.font()
        f.fromString(prefs.settings.log_font)
        self.textLog.setFont(f)

    def prefs_apply_font_size(self):
        f = self.textLog.font()
        f.setPointSize(prefs.settings.log_font_size)
        self.textLog.setFont(f)

    def save_settings(self):
        prefs.settings.set_value(
            prefs.SettingsItem("geometry", bytearray), bytearray(self.saveGeometry())
        )
        prefs.settings.set_value(
            prefs.SettingsItem("state", bytearray), bytearray(self.saveState())
        )
        prefs.settings.set_value(
            prefs.SettingsItem("checkList", list), self.treeTests.getCheckList()
        )
        prefs.settings.set_value(
            prefs.SettingsItem("foldList", list), self.treeTests.getFoldList()
        )
        self.treeTests.saveSizes()
        prefs.settings.sync()

    def closeEvent(self, event):
        self.on_exiting()
        event.accept()

    def on_exiting(self):
        try:
            if self.runner.state == TestState.IDLE:
                self.save_settings()
            self.file_manager.clear_process()
        finally:
            self.threadTestStatus.stop()
            self.threadOutput.stop()
            self.threadOutput.wait()
            self.threadTestStatus.wait()

    def show_checkboxes(self, hidden=None):
        if hidden:
            h = hidden
        else:
            h = prefs.settings.show_checkboxes
        if h:
            if hasattr(self, "treeTests"):
                self.disconnect_signals()
                self.treeTests.addCheckBoxes()
                self.reconnect_signals()
            self.checkSelect.setEnabled(True)
        else:
            if hasattr(self, "treeTests"):
                self.treeTests.checkUncheckAll(self.test_service, True)
                self.disconnect_signals()
                self.treeTests.removeCheckBoxes()
                self.reconnect_signals()
            self.checkSelect.setDisabled(True)

    def update_from_prefs(self):
        self.hide_doc_pane()
        self.hide_log_pane()

    def hide_doc_pane(self):
        if prefs.settings.hide_doc_pane:
            self.DocDockWidget.hide()
        else:
            self.DocDockWidget.show()

    def hide_log_pane(self):
        if prefs.settings.hide_log_pane:
            self.logDockWidget.hide()
        else:
            self.logDockWidget.show()

    def update_f1_window(self, tree_item):
        self.d_f1_win.ui.typeLineEdit.setText(tree_item.test_type)
        self.d_f1_win.ui.sequenceFileNameLineEdit.setText(tree_item.seq_filename)
        if tree_item.content is not None and tree_item.content != "":
            self.d_f1_win.ui.TestContentEdit.setText(tree_item.content)
        else:
            self.d_f1_win.ui.TestContentEdit.setText("")

    def _stripped_name(self, fullFileName):
        fname = os.path.basename(fullFileName)
        fdir = os.path.dirname(fullFileName)
        if len(fdir) > 30:
            return os.path.join("... " + fdir[30:], fname)
        else:
            return fullFileName

    def redirectStdToTextLog(self, txtlog=None):
        if txtlog is None:
            stdio_redir.restore()
        else:
            stdio_redir.redirect(txtlog)

    # --- Qt Slots (thin delegates) ---

    @Slot()
    def on_actionOpenTest_triggered(self):
        self.file_manager.on_open_test()

    @Slot()
    def on_actionStart_test_triggered(self):
        self.runner.on_start_test()

    def on_runFinished(self):
        self.runner.on_run_finished()

    @Slot()
    def on_actionStop_test_triggered(self):
        self.runner.on_stop_test()

    def on_breakpoint(self):
        self.runner.on_breakpoint()

    @Slot()
    def on_actionExit_triggered(self):
        self.close()

    @Slot()
    def on_actionAbout_testium_triggered(self):
        self.d_about_win.setVisible(True)

    @Slot()
    def on_actionPreferences_triggered(self):
        result = self.pref_win.exec()
        if result == QDialog.Accepted:
            self.update_from_prefs()
            if self.pref_win.isChanged(prefs.settings.SettingsShowCheckboxes):
                self.show_checkboxes()
            if self.pref_win.isChanged(prefs.settings.SettingsDblClickEnabled):
                if prefs.settings.dbl_click_enabled:
                    self.treeTests.itemDoubleClicked.connect(self.on_testItemDblClicked)
                else:
                    self.treeTests.itemDoubleClicked.disconnect()
            if self.pref_win.isChanged(prefs.settings.SettingsLogFont):
                self.prefs_apply_font()
            if self.pref_win.isChanged(prefs.settings.SettingsLogFontSize):
                self.prefs_apply_font_size()

    @Slot()
    def on_actionRefresh_test_triggered(self):
        if self.testFile:
            self.file_manager.reload(self.testFile)

    @Slot()
    def on_actionSave_report_triggered(self):
        if self.testFile:
            initialPath = os.path.dirname(self.testFile)
        else:
            initialPath = None
        fileName, _ = QFileDialog.getSaveFileName(
            self, "Path to Log file", initialPath, "Log Files (*.log);;All Files (*)"
        )
        if fileName:
            shutil.copy(self.logFileName, fileName)

    @Slot()
    def on_actionShow_Results_triggered(self):
        s = sys.platform
        self.statusBar().showMessage(
            "Opening the logfile (" + s + "): " + self.logFileName, 100000
        )
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.logFileName))

    @Slot()
    def on_actionHelp_triggered(self):
        self.webbrowser_open()

    def webbrowser_open(self):
        def open_browser_thread():
            webbrowser.open(
                "https://git.beafrancois.fr/v-and-v/testium/src/branch/main/doc/manual/testium_manual.pdf",
                new=2,
                autoraise=True,
            )
        thread = Thread(target=open_browser_thread)
        thread.daemon = True
        thread.start()

    @Slot()
    def on_actionTestInformation_triggered(self):
        if not self.d_f1_win.isVisible():
            self.d_f1_win.show()

    def on_buttLogFilePath_clicked(self):
        if self.editLogFilePath.text() != "":
            initialPath = os.path.dirname(self.editLogFilePath.text())
        elif self.testFile:
            initialPath = os.path.dirname(self.testFile)
        else:
            initialPath = None
        fileName, _ = QFileDialog.getSaveFileName(
            self, "Path to log file", initialPath, "Log Files (*.log);;All Files (*)"
        )
        if fileName:
            self.editLogFilePath.setText(fileName)
            self.on_configLog_changed()

    def on_selectDeselectAll(self):
        state = self.checkSelect.checkState()
        self.disconnect_signals()
        try:
            if state == Qt.Checked:
                self.treeTests.checkUncheckAll(self.test_service, True)
            elif state == Qt.Unchecked:
                self.treeTests.checkUncheckAll(self.test_service, False)
        finally:
            self.reconnect_signals()

    def on_testChecked(self, item, index):
        if index != self.treeTests.cols['name']['index']:
            return
        self.checkSelect.setCheckState(Qt.PartiallyChecked)
        self.disconnect_signals()
        try:
            self.treeTests.updateTreeCheckState(item, self.test_service)
        finally:
            self.reconnect_signals()

    @Slot()
    def on_testSelectionChanged(self):
        items = self.treeTests.selectedItems()
        if len(items) > 0:
            doc = items[0].doc
            tmstmp = items[0].timestamp()
            self.textEditTestDoc.setText("<b>" + items[0].name + ":</b><br>")
            if str(doc) != "":
                self.textEditTestDoc.append(doc)
            if tmstmp > 0:
                text = self.textLog.toPlainText()
                index = text.find(f"@@{tmstmp}@@")
                if index != -1:
                    cursor = self.textLog.textCursor()
                    cursor.setPosition(index)
                    self.textLog.setTextCursor(cursor)
                    block_number = cursor.blockNumber()
                    scrollbar = self.textLog.verticalScrollBar()
                    scrollbar.setValue(block_number)

            self.update_f1_window(items[0])
            if self.d_f1_win.isVisible():
                self.d_f1_win.raise_()

            if tmstmp > 0:
                cursor = self.textLog.textCursor()
                cursor.movePosition(QTextCursor.Start)
                self.textLog.setTextCursor(cursor)
                if self.textLog.find(f"@@{tmstmp}@@"):
                    cursor = self.textLog.textCursor()
                    ln = cursor.block().blockNumber()
                    self.textLog.verticalScrollBar().setValue(ln)
                    cursor.clearSelection()
                    self.textLog.setTextCursor(cursor)

    def on_testItemDblClicked(self, item, col):
        isBrkpointCol = item.setBreakpointIfCol(col)
        if isBrkpointCol:
            if item.isBreakpoint():
                self.test_service.add_breakpoint(item.id)
            else:
                self.test_service.del_breakpoint(item.id)
            return
        if (self.logFileName is not None) and os.access(self.logFileName, os.R_OK):
            ln = tm.line_number("@@{}@@".format(item.timestamp()), self.logFileName)
            if ln > 0:
                os.system("{} -g {}:{} &".format("code", self.logFileName, ln + 1))

    def on_spacePressed(self):
        item = self.treeTests.currentItem()
        add_breakpoint = item.setBreakpoint()
        if add_breakpoint:
            self.test_service.add_breakpoint(item.id)
        else:
            self.test_service.del_breakpoint(item.id)

    def on_F1Pressed(self):
        item = self.treeTests.currentItem()
        self.update_f1_window(item)
        self.d_f1_win.setVisible(True)

    def on_checkFoldChanged(self):
        self.disconnect_signals()
        try:
            if self.checkFold.checkState() != Qt.Unchecked:
                self.treeTests.foldAll(True)
                self.checkFold.setCheckState(Qt.Checked)
            else:
                self.treeTests.foldAll(False)
        finally:
            self.reconnect_signals()

    def on_itemFoldChanged(self):
        self.disconnect_signals()
        try:
            self.checkFold.setCheckState(Qt.PartiallyChecked)
        finally:
            self.reconnect_signals()

    def on_buttClearLog_clicked(self):
        self.textLog.clear()

    def on_buttGoBottom_clicked(self):
        self.textLog.moveCursor(QtGui.QTextCursor.End)
        self.textLog.ensureCursorVisible()

    def on_configLog_changed(self):
        prefs.settings.log_file = self.editLogFilePath.text()

    def on_configLogSaved_changed(self):
        prefs.settings.log_file_saved = self.buttLogFileSaved.isChecked()

    def on_configLogNone_changed(self):
        prefs.settings.log_file_saved = not self.buttLogFileNone.isChecked()

    def on_logToBeAppended(self, m):
        self.textLog.moveCursor(QtGui.QTextCursor.End)
        self.textLog.insertPlainText(m)

    # --- Blink delegates (kept for backward compatibility with treeTests signal) ---

    def setBlinkGreen(self):
        self.runner.set_blink_green()

    def setBlinkRed(self):
        self.runner.set_blink_red()

    def setBlinkGray(self):
        self.runner.set_blink_gray()


def MainWin(
    test_file=None,
    config_files="",
    run=False,
    log_file="",
    defines="",
    report="",
    report_type="",
    report_pattern=[],
    debug=False,
):
    app = QApplication(sys.argv)
    ui = MainWindow(
        test_file,
        config_files,
        run,
        log_file,
        defines,
        report,
        report_type,
        report_pattern,
        debug,
    )

    import signal
    import os as _os

    def _sigabrt_handler(signum, frame):
        # Qt crash: exit with the test result if known, -1 if test never completed
        _os._exit(ui.run_exit_code)

    signal.signal(signal.SIGABRT, _sigabrt_handler)

    ui.show()
    app.exec_()
    exit_code = ui.run_exit_code if ui.run_exit_code >= 0 else 0
    del ui
    sys.exit(exit_code)
