import sys
import os
import subprocess
import traceback
import webbrowser
from time import sleep
from tempfile import NamedTemporaryFile
from multiprocessing import Queue
from queue import Empty
from threading import Thread
import shutil
import ast

# Qt
from PySide6 import QtGui, QtWidgets
from PySide6.QtGui import QAction, QShortcut, QIcon, QPixmap, QTextCursor, QDesktopServices, QTextCursor
from PySide6.QtCore import Slot, QUrl, Qt, QTimer, QDateTime

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
from interpreter.utils.string_queue import StringQueue
from interpreter.process import TestProcess
from interpreter.utils.test_ctrl import TestSetController
from interpreter.utils.icons import icon_prefix

from main_win.test_run.outlog import OutLog
from main_win.test_run.test_run import ThreadTestStatus
import interpreter.utils.settings as prefs
from interpreter.utils.stdout_redirect import stdio_redir
import libs.testium as tm
from interpreter.utils.version import get_testium_version
from interpreter.utils.test_init import (
    env_init,
    locate_report_file,
)
from interpreter.utils.tum_except import ETUMFileError, ETUMRuntimeError


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

        icon2 = QtGui.QIcon()
        icon2.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/edit-clear.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.buttClearLog.setIcon(icon2)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/go-bottom.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.buttGoBottom.setIcon(icon3)
        icon4 = QtGui.QIcon()
        icon4.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/document-open.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionOpenTest.setIcon(icon4)
        icon5 = QtGui.QIcon()
        icon5.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/document-save.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionSave_report.setIcon(icon5)
        icon6 = QtGui.QIcon()
        icon6.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/start.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionStart_test.setIcon(icon6)
        icon7 = QtGui.QIcon()
        icon7.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/stop.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionStop_test.setIcon(icon7)
        icon8 = QtGui.QIcon()
        icon8.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/about.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionAbout_testium.setIcon(icon8)
        icon9 = QtGui.QIcon()
        icon9.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/exit.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionExit.setIcon(icon9)
        icon10 = QtGui.QIcon()
        icon10.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/view-refresh.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionRefresh_test.setIcon(icon10)
        icon11 = QtGui.QIcon()
        icon11.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/results.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionShow_Results.setIcon(icon11)
        icon12 = QtGui.QIcon()
        icon12.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/help.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionHelp.setIcon(icon12)
        icon13 = QtGui.QIcon()
        icon13.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/settings.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionPreferences.setIcon(icon13)

        icon14 = QtGui.QIcon()
        icon14.addPixmap(
            QtGui.QPixmap(icon_prefix() + "/info.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.actionTestInformation.setIcon(icon14)

        self.runandclose = runandclose
        # Var init
        self.mainWindowTitle = self.windowTitle()
        self.logFileHandler = None
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
        self.threadTestStatus = None
        self._test_started = False
        self._test_paused = False
        self._signals_connected = False

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
        self.setBlinkGreen()

        self.threads_queue = Queue()
        self.status_queue = Queue()

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

        # disable the action buttons
        self.actionStart_test.setDisabled(True)
        self.actionShow_Results.setDisabled(True)
        self.actionSave_report.setDisabled(True)

        # Tree Test
        self.create_tree()

        # Shortcuts
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

        # Main Window items modifications
        self.actionRefresh_test.setDisabled(True)

        # Connection of the handlers
        self.buttLogFilePath.pressed.connect(self.on_buttLogFilePath_clicked)
        self.buttClearLog.pressed.connect(self.on_buttClearLog_clicked)
        self.buttGoBottom.pressed.connect(self.on_buttGoBottom_clicked)
        self.editLogFilePath.editingFinished.connect(self.on_configLog_changed)
        self.buttLogFileSaved.toggled.connect(self.on_configLogSaved_changed)
        self.buttLogFileNone.toggled.connect(self.on_configLogNone_changed)
        self.timer.timeout.connect(self.on_timerEvent)
        self.timerBlink.timeout.connect(self.on_timerBlinkEvent)
        self.timerBlink.timeout.connect(self.on_timerCount)
        self.timerPause.timeout.connect(self.on_timerPause)
        self.treeTests.itemSelectionChanged.connect(self.on_testSelectionChanged)
        if prefs.settings.dbl_click_enabled:
            self.treeTests.setExpandsOnDoubleClick(False)
            self.treeTests.itemDoubleClicked.connect(self.on_testItemDblClicked)
        else:
            self.treeTests.setExpandsOnDoubleClick(True)
        QApplication.instance().lastWindowClosed.connect(self.on_exiting)

        self.prefs_apply_font()
        self.prefs_apply_font_size()

        # Recent files
        for i in range(MainWindow.MaxRecentFiles):
            self.recentFileActs.append(
                QAction(self, visible=False, triggered=self.on_openRecentFile)
            )
        self.separatorAct = self.menuFile.addSeparator()
        for i in range(MainWindow.MaxRecentFiles):
            self.menuFile.addAction(self.recentFileActs[i])
        self.updateRecentFileActions()

        # A propos
        self.d_about_win = QDialog()
        self.about_win = Ui_About()

        self.about_win.setupUi(self.d_about_win)
        self.about_win.labelVersion.setText("testium - " + get_testium_version())
        self.about_win.labelCesUnitVersion.setText("")
        self.d_about_win.setModal(True)

        # F1 window
        self.d_f1_win = DialogF1(self)

        self.stream = StringQueue()  # stream used to log output
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

        # report file name treatment
        self.reportFileName = locate_report_file(self.reportFileName)

        # open the last opened file if it exists.

        last_files = prefs.settings.recent_files
        ret = False
        if test_file != "":
            if not os.path.isabs(test_file):
                test_file = os.path.join(os.getcwd(), test_file)
            if os.path.isfile(test_file):
                ret = self.loadTestSetFile(test_file)
        elif (len(last_files) > 0) and os.path.isfile(last_files[0]):
            ret = self.loadTestSetFile(last_files[0])

        # In case of successfull loading of a file, we need to update the fold and checked state
        if ret:
            self.file_loaded_at_startup()

        # connect the test status
        self.threadTestStatus.testSetIsFinished.connect(self.on_runFinished)
        self.threadTestStatus.statusToBeUpdated.connect(self.treeTests.updateStatus)
        self.reconnect_signals()

        if runandclose:
            self.on_actionStart_test_triggered()

    def create_text_log(self, parent):
        textLog = QTextLog(parent)
        return textLog

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

        # Apply production/Lab state
        if modeSlider_value:
            # restore check boxes state if in lab mode
            checkList = prefs.settings.value(prefs.SettingsItem("checkList", list), [])
            if checkList is not None:
                if len(checkList) == self.treeTests.getItemCount():
                    self.treeTests.restoreCheckList(checkList, self.ts_controller)

                else:
                    tm.print_info(
                        "The number of tests has changed. Test box states are not restored."
                    )

        # Apply treeview visibility
        foldList = prefs.settings.value(prefs.SettingsItem("foldList", list), [])
        if foldList:
            if len(foldList) == self.treeTests.getItemCount():
                self.checkFold.setCheckState(Qt.PartiallyChecked)
                self.treeTests.restoreFoldList(foldList)

    def disconnect_signals(self):
        if self._signals_connected:
            # disconnect the GUI
            self.checkSelect.stateChanged.disconnect()
            self.treeTests.itemChanged.disconnect()
            self.checkFold.stateChanged.disconnect()
            self.treeTests.itemCollapsed.disconnect()
            self.treeTests.itemExpanded.disconnect()
            self._signals_connected = False

    def reconnect_signals(self):
        if not self._signals_connected:
            # reconnect the GUI
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

    def reload_test_set_file(self, file_name: str):
        self.disconnect_signals()
        self.clear_process()
        self.loadTestSetFile(file_name)
        self.reconnect_signals()

    def clear_process(self):
        if (
            self.test_proc is not None
            and self.test_proc.is_alive()
            and (self.ts_controller is not None)
        ):
            self.ts_controller.control("stop")
            self.ts_controller.control("close")
            self.test_proc.join()
            del self.test_proc
            self.test_proc = None
            del self.ts_controller
            self.ts_controller = None

    @Slot()
    def on_actionOpenTest_triggered(self):
        d = ""
        if self.testFile is not None:
            d = os.path.dirname(self.testFile)
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open the test file", d, "testium file (*.tum);;All Files (*)"
        )
        if file_name:
            self.reload_test_set_file(file_name)

    def startPauseTimer(self):
        self.timerPause.setSingleShot(False)
        self.timerPause.setInterval(500)
        self.timerPause.start()
        self.timerPause.state = False

    @Slot()
    def on_actionStart_test_triggered(self):
        # Test to be paused
        if self._test_started:
            if not self._test_paused:
                self.ts_controller.control("pause")
                self.startPauseTimer()
            else:

                # Test to be continued
                self.ts_controller.control("cont")
                self.timerPause.stop()
                self.timerPause.state = False
                self.on_timerPause()

            self._test_paused = not self._test_paused
            return

        # Test to be started
        self.start_time = QDateTime.currentDateTime()

        # log file definition
        log_file = self.editLogFilePath.text()
        if self.buttLogFileSaved.isChecked() and (log_file != ""):
            try:
                if not os.path.isabs(log_file):
                    default_path = prefs.settings.log_path
                    default_path = self.ts_controller.control(
                        "process_param", param=default_path
                    )
                    log_file = os.path.join(default_path, log_file)
                # if the directory does not exist
                if not os.path.exists(os.path.dirname(log_file)):
                    os.makedirs(os.path.dirname(log_file))
                # If the file exists
                if os.path.isfile(log_file):
                    i = 0
                    fname = log_file
                    while os.path.isfile(fname):
                        i += 1
                        fname = log_file + "-" + str(i) + ".saved"

                    os.rename(log_file, fname)
                self.logFileHandler = open(log_file, "w")
                self.out_log.set(self.logFileHandler)
                self.logFileName = log_file
            except:
                self.logFileHandler = NamedTemporaryFile(
                    mode="w", suffix=".log", delete=False
                )
                self.out_log.set(self.logFileHandler)
                self.logFileName = self.logFileHandler.name
        else:
            self.logFileHandler = NamedTemporaryFile(
                mode="w", suffix=".log", delete=False
            )
            self.out_log.set(self.logFileHandler)
            self.logFileName = self.logFileHandler.name

        # Report file definition
        rep_file = self.ts_controller.control(
            "process_param", param=self.reportFileName
        )
        self.ts_controller.control(
            "report",
            rep_path=rep_file,
            rep_type=self.report_type,
            pattern=self.report_pattern,
        )
        self.adaptInterfaceDuringTest()
        self.treeTests.clearAllStatus()
        try:
            self.textLog.clear()
            self.textLog.appendPlainText("Test is started\n")
            self.timer.setSingleShot(False)
            self.timer.setInterval(100)
            self.timer.start()
            # Add the log file to the std test_outputs
            self.ts_controller.control("set_test_outputs", outputs=[self.logFileName])
            # Launch the test
            self.ts_controller.control("execute")
        except:
            print(traceback.format_exc())
            self.restoreInterfaceAfterTest()

    def on_runFinished(self):
        self.timer.setSingleShot(True)
        self.timer.setInterval(1000)
        txt = self.stream.read()
        self.textLog.appendPlainText(txt)
        self.restoreInterfaceAfterTest()

        if self.logFileHandler is not None:
            self.out_log.reset()
            self.logFileHandler.write(txt + "\n")
            self.logFileHandler.close()

        self.logFileHandler = None

        self.textLog.appendPlainText("Test is finished")
        if self.runandclose:
            self.on_actionExit_triggered()

    @Slot()
    def on_actionStop_test_triggered(self):
        self.ts_controller.control("stop")

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

    @Slot()
    def on_actionExit_triggered(self):
        self.close()

    def on_exiting(self):
        if not self._test_started:
            self.save_settings()
        self.clear_process()
        self.threadTestStatus.stop()
        self.threadOutput.stop()
        self.threadOutput.wait()
        self.threadTestStatus.wait()

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
        self.on_exiting()
        args = []
        if not hasattr(sys, "frozen"):
            args += [sys.executable]
        args += [sys.argv[0]]

        if len(self.defines) > 0:
            for k, v in self.defines.items():
                try:
                    val = ast.literal_eval(v)
                except:
                    val = v

                args += ["-d", f"{k}={val}"]

        if (self.testFile is not None) and (isinstance(self.testFile, str)):
            args += [self.testFile]

        os.execv(sys.executable, args)

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

    def on_openRecentFile(self):
        action = self.sender()
        if action:
            self.reload_test_set_file(action.data())

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
                self.treeTests.checkUncheckAll(self.ts_controller, True)
            elif state == Qt.Unchecked:
                self.treeTests.checkUncheckAll(self.ts_controller, False)
        finally:
            self.reconnect_signals()

    def on_testChecked(self, item, index):
        self.checkSelect.setCheckState(Qt.PartiallyChecked)
        self.disconnect_signals()
        try:
            self.treeTests.updateTreeCheckState(item, self.ts_controller)
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
                    # obtain the vertical position of the cursor
                    block_number = cursor.blockNumber()
                    scrollbar = self.textLog.verticalScrollBar()
                    # Position the vert scrollbar to the right location
                    scrollbar.setValue(block_number)

            # Content of the F1 window is updated
            self.update_f1_window(items[0])
            if self.d_f1_win.isVisible():
                self.d_f1_win.raise_()

            # When the test is selected, an attemp to move the log edit
            # to the test is done.
            # rmk: it has no effect when test is running. It is due to QPlainTextEdit
            # limitations
            if tmstmp > 0:
                # Place the cursor at the begining of the text
                cursor = self.textLog.textCursor()
                cursor.movePosition(QTextCursor.Start)
                self.textLog.setTextCursor(cursor)
                # Find the timestamp
                if self.textLog.find(f"@@{tmstmp}@@"):
                    cursor = self.textLog.textCursor()
                    ln = cursor.block().blockNumber()
                    # Move the scrollbar to the text
                    self.textLog.verticalScrollBar().setValue(ln)
                    cursor.clearSelection()
                    self.textLog.setTextCursor(cursor)

    def on_testItemDblClicked(self, item, col):
        isBrkpointCol = item.setBreakpointIfCol(col)
        if isBrkpointCol:
            if item.isBreakpoint():
                self.ts_controller.control("add_breakpoint", item_id=item.id)
            else:
                self.ts_controller.control("del_breakpoint", item_id=item.id)
            return

        s = sys.platform

        if (self.logFileName is not None) and os.access(self.logFileName, os.R_OK):
            ln = tm.line_number("@@{}@@".format(item.timestamp()), self.logFileName)

            if ln > 0:
                os.system("{} -g {}:{} &".format("code", self.logFileName, ln + 1))

    def on_spacePressed(self):
        item = self.treeTests.currentItem()
        add_breakpoint = item.setBreakpoint()
        if add_breakpoint:
            self.ts_controller.control("add_breakpoint", item_id=item.id)
        else:
            self.ts_controller.control("del_breakpoint", item_id=item.id)

    def on_F1Pressed(self):
        item = self.treeTests.currentItem()
        self.update_f1_window(item)
        self.d_f1_win.setVisible(True)

    # @Slot()
    def on_breakpoint(self):
        self._test_paused = True
        self.startPauseTimer()

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

    def on_timerEvent(self):
        text_to_append = []
        while not self.threads_queue.empty():
            text_to_append.append(self.threads_queue.get())

        if len(text_to_append) > 0:
            for t in text_to_append:
                self.textLog.appendPlainText(t)

                if self.logFileHandler is not None:
                    self.logFileHandler.write(t + "\n")
                    self.logFileHandler.flush()
                    # os.fsync(self.logFileHandler)

    def on_timerBlinkEvent(self):
        if self.buttBlink.current_color != "gray":
            self.setBlinkGray()
        elif self.treeTests.getGlobalSuccess():
            self.setBlinkGreen()
        else:
            self.setBlinkRed()

    def on_timerPause(self):
        if self._test_paused:
            icon = QtGui.QIcon()
            if self.timerPause.state:
                icon.addPixmap(
                    QtGui.QPixmap(icon_prefix() + "/pause2.png"),
                    QtGui.QIcon.Normal,
                    QtGui.QIcon.Off,
                )
            else:
                icon.addPixmap(
                    QtGui.QPixmap(icon_prefix() + "/pause.png"),
                    QtGui.QIcon.Normal,
                    QtGui.QIcon.Off,
                )
            self.timerPause.state = not self.timerPause.state
            self.actionStart_test.setIcon(icon)

    def on_timerCount(self):
        secfromstart = self.start_time.secsTo(QDateTime.currentDateTime())
        self.label_runtime.setText(
            "%02d:%02d:%02d"
            % (secfromstart / 3600, (secfromstart / 60) % 60, secfromstart % 60)
        )

    def on_logToBeAppended(self, m):
        self.textLog.moveCursor(QtGui.QTextCursor.End)
        self.textLog.insertPlainText(m)

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

    def show_checkboxes(self, hidden=None):
        if hidden:
            h = hidden
        else:
            h = prefs.settings.show_checkboxes
        if h:
            # lab mode
            if hasattr(self, "treeTests"):
                self.disconnect_signals()
                self.treeTests.addCheckBoxes()
                self.reconnect_signals()
            self.checkSelect.setEnabled(True)
        else:
            # production mode
            if hasattr(self, "treeTests"):
                self.treeTests.checkUncheckAll(self.ts_controller, True)
                self.disconnect_signals()
                self.treeTests.removeCheckBoxes()
                self.reconnect_signals()
            self.checkSelect.setDisabled(True)

    def addFileToRecent(self, filename):
        files = prefs.settings.recent_files

        try:
            files.remove(filename)
        except ValueError:
            pass

        files.insert(0, filename)
        del files[MainWindow.MaxRecentFiles :]

        prefs.settings.recent_files = files

        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, MainWindow):
                widget.updateRecentFileActions()

    def updateRecentFileActions(self):
        files = prefs.settings.recent_files

        numRecentFiles = min(len(files), MainWindow.MaxRecentFiles)

        for i in range(numRecentFiles):
            text = "&%d %s" % (i + 1, self.strippedName(files[i]))
            self.recentFileActs[i].setText(text)
            self.recentFileActs[i].setData(files[i])
            self.recentFileActs[i].setVisible(True)

        for j in range(numRecentFiles, MainWindow.MaxRecentFiles):
            self.recentFileActs[j].setVisible(False)

        self.separatorAct.setVisible((numRecentFiles > 0))

    def update_f1_window(self, tree_item):
        self.d_f1_win.ui.typeLineEdit.setText(tree_item.test_type)
        self.d_f1_win.ui.sequenceFileNameLineEdit.setText(tree_item.seq_filename)
        if tree_item.content is not None and tree_item.content != "":
            self.d_f1_win.ui.TestContentEdit.setText(tree_item.content)
        else:
            self.d_f1_win.ui.TestContentEdit.setText("")

    def strippedName(self, fullFileName):
        fname = os.path.basename(fullFileName)
        fdir = os.path.dirname(fullFileName)
        if len(fdir) > 30:
            return os.path.join("... " + fdir[30:], fname)
        else:
            return fullFileName

    def defaults_for_process(self):
        d = {}

        pp = prefs.settings.python_bin
        if pp != "":
            d["python_bin"] = pp

        pp = prefs.settings.lua_bin
        if pp != "":
            d["lua_bin"] = pp

        return d

    def loadTestSetFile(self, file_name):
        """Load the tests:
        return True if it succeeds, False otherwise.
        """
        try:
            if not file_name:
                raise ETUMFileError("No file to load")

            file_name = os.path.abspath(file_name)
            initial_dir = os.path.dirname(file_name)

            if not os.path.isdir(initial_dir):
                raise ETUMFileError("Could not find %s directory" % (initial_dir))
            if not os.path.isfile(file_name):
                raise ETUMFileError("Could not find %s file" % (file_name))

            self.testFile = None
            self.ts_controller = TestSetController()
            self.test_proc = TestProcess(
                file_name,
                self.status_queue,
                self.ts_controller,
                self.config_files,
                self.defines,
                self.defaults_for_process(),
            )
            self.test_proc.start()
            while self.test_proc.is_alive():
                try:
                    if self.ts_controller.control("loaded", timeout=1.0):
                        break
                except Empty:
                    self.ts_controller.clear()

            if not self.test_proc.is_alive():
                del self.test_proc
                self.test_proc = None
                del self.ts_controller
                self.ts_controller = None

                raise ETUMRuntimeError(
                    "Test could not be loaded (test process crashed for any reason)"
                )

            test_data = self.ts_controller.control("tree")
            self.treeTests.clear()
            self.treeTests.loadTestRecursively(
                self.treeTests.invisibleRootItem(), test_data
            )
            self.treeTests.setFoldDefault()
            self.treeTests.updateTreeSkipState(self.ts_controller)

            self.checkSelect.setChecked(True)
            self.testFile = file_name
            test_dir = os.path.dirname(self.testFile)

            sys.path.append(test_dir)
            self.statusBar().showMessage("Test file loaded", 10000)
            self.textLog.set_test_dir(test_dir)
            self.addFileToRecent(file_name)
            self.setWindowTitle(self.mainWindowTitle + " - " + self.testFile)
            self.actionStart_test.setEnabled(True)
            self.actionRefresh_test.setEnabled(True)

            self.show_checkboxes()
            return True
        except:
            self.statusBar().showMessage("No test file could be loaded", 10000)
            self.treeTests.clear()
            print(traceback.format_exc())
            return False

    def adaptInterfaceDuringTest(self):
        try:
            self.disconnect_signals()
            # disable run and reload button
            self.actionOpenTest.setDisabled(True)
            self.actionExit.setDisabled(True)
            icon = QtGui.QIcon()
            icon.addPixmap(
                QtGui.QPixmap(icon_prefix() + "/pause.png"),
                QtGui.QIcon.Normal,
                QtGui.QIcon.Off,
            )
            self.actionStart_test.setIcon(icon)
            self.actionStart_test.setText("Pause test")
            self.actionPreferences.setDisabled(True)
            self.actionRefresh_test.setDisabled(True)
            self.actionShow_Results.setDisabled(True)
            self.actionSave_report.setDisabled(True)
            self.logSettingsBox.setDisabled(True)
            self.actionStop_test.setEnabled(True)
            if prefs.settings.show_checkboxes:
                self._checklist = self.treeTests.getCheckList()
                self.treeTests.removeCheckBoxes()
            self.checkSelect.setDisabled(True)
            self.checkFold.setDisabled(True)
            self.timerBlink.setSingleShot(False)
            self.timerBlink.setInterval(1000)
            self.timerBlink.start()
            self.setBlinkGreen()
            self.treeTests.clearGlobalSuccess()
        finally:
            self._test_started = True

    def restoreInterfaceAfterTest(self):
        try:
            self.timerPause.stop()
            self.timerBlink.stop()
            # enable run and reload button
            self.actionOpenTest.setEnabled(True)
            self.actionExit.setEnabled(True)
            icon = QtGui.QIcon()
            icon.addPixmap(
                QtGui.QPixmap(icon_prefix() + "/start.png"),
                QtGui.QIcon.Normal,
                QtGui.QIcon.Off,
            )
            self.actionStart_test.setIcon(icon)
            self.actionStart_test.setText("Start test")
            self.actionPreferences.setEnabled(True)
            self.actionRefresh_test.setEnabled(True)
            self.actionStop_test.setDisabled(True)
            self.actionShow_Results.setEnabled(True)
            self.actionSave_report.setEnabled(True)
            self.logSettingsBox.setEnabled(True)
            if prefs.settings.show_checkboxes:
                self.checkSelect.setEnabled(True)
                self.treeTests.showCheckBoxes(self._checklist, self.ts_controller)
            self.checkFold.setEnabled(True)
            self.treeTests.setChildrenEnabled()
            self.reconnect_signals()
            if self.treeTests.getGlobalSuccess():
                self.setBlinkGreen()
            else:
                self.setBlinkRed()
        finally:
            self._test_started = False

    def redirectStdToTextLog(self, txtlog=None):
        if txtlog is None:
            stdio_redir.restore()
        else:
            stdio_redir.redirect(txtlog)

    def setBlinkGreen(self):
        self.buttBlink.setIcon(self.iconBlinkGreen)
        self.buttBlink.current_color = "green"

    def setBlinkRed(self):
        self.buttBlink.setIcon(self.iconBlinkRed)
        self.buttBlink.current_color = "red"

    def setBlinkGray(self):
        self.buttBlink.setIcon(self.iconBlinkGray)
        self.buttBlink.current_color = "gray"


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

    ui.show()
    sys.exit(app.exec_())
