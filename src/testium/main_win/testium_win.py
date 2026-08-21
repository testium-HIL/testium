import sys
import os
import shlex
import subprocess
import webbrowser
import hashlib
import time
from multiprocessing import Queue
from threading import Thread
import shutil

# Qt
from PySide6 import QtGui
from PySide6.QtGui import QAction, QShortcut, QIcon, QPixmap, QTextCursor, QDesktopServices, QKeySequence
from PySide6.QtCore import Slot, QUrl, Qt, QTimer, QSize

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QFileDialog,
    QSizePolicy,
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QCheckBox,
    QLabel,
    QToolButton,
    QToolBar,
    QMenu,
    QVBoxLayout,
    QDialogButtonBox,
)
from main_win.expression_info import expression_info_button

ourPath = os.path.dirname(__file__)
sys.path.append(os.path.join(ourPath, "resources"))

# user interfaces
from main_win.testium_core_win import Ui_MainWindow
from main_win.text_log import QTextLog
from main_win.about_win.about_win import Ui_About
from main_win.preference_win.preference_win import PrefWindow
from main_win.variables_dock import VariablesDock
from main_win.item_dock import ItemDock
from main_win.test_tree import QTestTree

from main_win.test_run.thread_output import ThreadTestOutput
from runtime.string_queue import StringQueue
from interpreter.utils.icons import icon_prefix
from interpreter.utils import bins

from main_win.test_run.outlog import OutLog
from main_win.test_run.test_run import ThreadTestStatus
from main_win import file_dialog
import interpreter.utils.settings as prefs
from interpreter.utils.constants import TestItemType as cst
from runtime.stdout_redirect import stdio_redir
import api.testium as tm
from interpreter.utils.test_init import (
    env_init,
    locate_report_file,
)
from interpreter.utils.version import get_testium_version
from runtime.tum_except import ETUMRuntimeError
from gui.run_presenter import RunPresenter, TestState
from gui.protocols import RunUiState
from main_win.qt_scheduler import QtScheduler
from main_win.test_file_manager import TestFileManager


class MainWindow(QMainWindow, Ui_MainWindow):
    MaxRecentFiles = 10
    # Window-state schema: bumped when docks/toolbars change shape, so
    # pre-0.5 blobs are rejected and the default layout applies.
    STATE_VERSION = 1

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
        self.textLog = self.create_text_log(self.logViewFrame)
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

        self.iconBlinkGreen = QIcon()
        self.iconBlinkGreen.addPixmap(QPixmap(icon_prefix() + "/green.png"))
        self.iconBlinkRed = QIcon()
        self.iconBlinkRed.addPixmap(QPixmap(icon_prefix() + "/red.png"))
        self.iconBlinkGray = QIcon()
        self.iconBlinkGray.addPixmap(QPixmap(icon_prefix() + "/gray.png"))

        self.threads_queue = Queue()
        self.status_queue = Queue()

        # Presenters / managers
        self.scheduler = QtScheduler(self)
        self.runner = RunPresenter(self, self.scheduler,
                                   lambda: self.test_service,
                                   self.threads_queue)
        self.runner.runandclose = runandclose
        self.file_manager = TestFileManager(self)

        self.runner.set_blink_green()

        env_init()

        # Persistence
        self.pref_win = PrefWindow(self)

        lastLog = prefs.settings.log_file
        self._cli_log_file = self.logFileName != ""
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

        # Built before restoreState so their positions are part of the
        # saved window state.
        self._build_step_bar()
        self.variablesDock = VariablesDock(self)
        self.itemDock = ItemDock(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.itemDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.variablesDock)

        state_settings = prefs.settings.value(
            prefs.SettingsItem("state", bytearray), bytearray()
        )
        restored = bool(state_settings) and self.restoreState(
            bytes(state_settings), self.STATE_VERSION)
        if not restored:
            # Pre-0.5 state blob (or none): default layout, honoring the
            # retired pane-hiding preferences once.
            self._apply_default_layout()
            if prefs.settings.hide_doc_pane:
                self.DocDockWidget.hide()
            if prefs.settings.hide_log_pane:
                self.logDockWidget.hide()
        # AFTER restoreState, which restores the corner ownership saved
        # with the blob. Side columns own their bottom corners: a dock
        # dropped in the bottom area sits under the tree, not across the
        # window.
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        self.stepBar.setVisible(True)
        self._update_step_bar_style()
        self._build_view_menu()

        # Toolbar shortcuts forcing a closed panel back on screen.
        self.actionVariables = QAction("Variables", self)
        icon = QIcon()
        icon.addPixmap(QPixmap(icon_prefix() + "/let.png"))
        self.actionVariables.setIcon(icon)
        self.actionVariables.setToolTip("Show the Variables panel")
        self.actionVariables.triggered.connect(
            self.on_actionVariables_triggered)
        self.toolBar.insertAction(self.actionSave_report,
                                  self.actionVariables)
        self.actionTestInformation.setToolTip("Show the Test item panel")

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

        self._search_matches = []
        self._search_idx = 0
        self._build_search_bar()
        self.shortcut_find = QShortcut(
            QKeySequence.Find, self, activated=self._toggle_search
        )

        self.actionRefresh_test.setDisabled(True)

        # Signal connections. clicked (release), not pressed: standard button
        # behavior; connectSlotsByName does not bind these undecorated slots.
        self.buttLogFilePath.clicked.connect(self.on_buttLogFilePath_clicked)
        self.buttClearLog.clicked.connect(self.on_buttClearLog_clicked)
        self.buttGoBottom.clicked.connect(self.on_buttGoBottom_clicked)
        self.editLogFilePath.editingFinished.connect(self.on_configLog_changed)
        self.buttLogFileSaved.toggled.connect(self.on_configLogSaved_changed)
        self.buttLogFileSaved.toggled.connect(self.editLogFilePath.setEnabled)
        self.buttLogFileSaved.toggled.connect(self.buttLogFilePath.setEnabled)
        self.editLogFilePath.setEnabled(self.buttLogFileSaved.isChecked())
        self.buttLogFilePath.setEnabled(self.buttLogFileSaved.isChecked())
        self.treeTests.itemSelectionChanged.connect(self.on_testSelectionChanged)
        if prefs.settings.dbl_click_enabled:
            self.treeTests.setExpandsOnDoubleClick(False)
            self.treeTests.itemDoubleClicked.connect(self.on_testItemDblClicked)
        else:
            self.treeTests.setExpandsOnDoubleClick(True)
        self.treeTests.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeTests.customContextMenuRequested.connect(
            self.on_testTreeContextMenu)

        self.prefs_apply_font()
        self.prefs_apply_font_size()

        # Recent files menu
        for i in range(MainWindow.MaxRecentFiles):
            self.recentFileActs.append(
                QAction(self, visible=False, triggered=self.file_manager.on_open_recent_file)
            )
        self.separatorAct = self.menuFile.addSeparator()
        # Hover shows the full path (menus hide action tooltips by default).
        self.menuFile.setToolTipsVisible(True)
        for i in range(MainWindow.MaxRecentFiles):
            self.menuFile.addAction(self.recentFileActs[i])
        self.file_manager.update_recent_file_actions()

        # Secondary windows
        self.d_about_win = QDialog()
        self.about_win = Ui_About()
        self.about_win.setupUi(self.d_about_win)
        self.about_win.labelVersion.setText(get_testium_version())
        self.d_about_win.setModal(True)

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

        self.reportFileName = locate_report_file(self.reportFileName)

        last_files = prefs.settings.recent_files
        ret = False
        if test_file:
            if not os.path.isabs(test_file):
                test_file = os.path.join(os.getcwd(), test_file)
            if os.path.isfile(test_file):
                ret = self.file_manager.load(test_file)
        elif (len(last_files) > 0) and os.path.isfile(last_files[0]):
            ret = self.file_manager.load(last_files[0])

        if ret:
            self.restore_file_state()

        self.threadTestStatus.testSetIsFinished.connect(self.runner.on_run_finished)
        self.threadTestStatus.statusToBeUpdated.connect(self.treeTests.updateStatus)
        self.threadTestStatus.gdUpdated.connect(self.variablesDock.gd_var_updated)
        self.threadTestStatus.gdDeleted.connect(self.variablesDock.gd_var_deleted)
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
            self.actionStep_over:       "step-over",
            self.actionStep_into:       "step-into",
            self.actionStep_out:        "step-out",
            self.actionAbout_testium:   "about",
            self.actionExit:            "exit",
            self.actionRefresh_test:    "view-refresh",
            self.actionShow_Results:    "results",
            self.actionHelp:            "help",
            self.actionPreferences:     "settings",
            self.actionTestInformation: "info",
            self.actionDebugOutput:     "bug",
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
        self.treeTests = QTestTree(self.centralColumn)
        self.treeTests.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeTests.sizePolicy().hasHeightForWidth())
        self.treeTests.setSizePolicy(sizePolicy)
        self.treeTests.paused.connect(self.on_paused)
        self.verticalLayout.addWidget(self.treeTests)

    # ---- test-tree search ---------------------------------------------------

    def _build_search_bar(self):
        """Find bar (Ctrl+F): highlight + navigate matches; Name/Type/Doc pick fields."""
        self.searchBar = QWidget(self.centralColumn)
        lay = QHBoxLayout(self.searchBar)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(4)

        self.searchEdit = QLineEdit(self.searchBar)
        self.searchEdit.setPlaceholderText("Search the test tree…")
        self.searchEdit.setClearButtonEnabled(True)
        lay.addWidget(self.searchEdit, 1)

        self.cbSearchName = QCheckBox("Name", self.searchBar)
        self.cbSearchType = QCheckBox("Type", self.searchBar)
        self.cbSearchDoc = QCheckBox("Doc", self.searchBar)
        for cb in (self.cbSearchName, self.cbSearchType, self.cbSearchDoc):
            cb.setChecked(True)
            cb.toggled.connect(self._do_search)
            lay.addWidget(cb)

        self.searchCount = QLabel("", self.searchBar)
        lay.addWidget(self.searchCount)

        self.searchPrev = QToolButton(self.searchBar)
        self.searchPrev.setArrowType(Qt.UpArrow)
        self.searchPrev.setToolTip("Previous match")
        self.searchPrev.clicked.connect(self._search_prev)
        lay.addWidget(self.searchPrev)

        self.searchNext = QToolButton(self.searchBar)
        self.searchNext.setArrowType(Qt.DownArrow)
        self.searchNext.setToolTip("Next match (Enter)")
        self.searchNext.clicked.connect(self._search_next)
        lay.addWidget(self.searchNext)

        self.searchClose = QToolButton(self.searchBar)
        self.searchClose.setText("✕")
        self.searchClose.setToolTip("Close (Esc)")
        self.searchClose.clicked.connect(self._close_search)
        lay.addWidget(self.searchClose)

        self.searchEdit.textChanged.connect(self._do_search)
        self.searchEdit.returnPressed.connect(self._search_next)
        QShortcut(Qt.Key_Escape, self.searchEdit,
                  context=Qt.WidgetShortcut, activated=self._close_search)

        # Insert above the tree (index 0 is the control row from setupUi).
        self.verticalLayout.insertWidget(1, self.searchBar)
        self.searchBar.setVisible(False)

    def _build_step_bar(self):
        """Movable run/debug bar, always visible: Start (Pause), Stop,
        then the step actions. Docked after the main toolbar by default;
        can be dragged elsewhere or detached (floating) — the position is
        kept in the window state. Large (main-toolbar style) when docked
        in the top area, compact icon-only anywhere else. The actions are
        shared with the Test menu (shortcuts stay global)."""
        self.stepBar = QToolBar("Run", self)
        self.stepBar.setObjectName("stepBar")
        self.stepBar.setMovable(True)
        self.stepBar.setFloatable(True)
        # Created before the Debug setChecked below: its toggled slot walks
        # every step action, this one included.
        self.actionRerun_step = QAction("Re-run last step", self)
        self.actionRerun_step.setShortcut(QKeySequence("Shift+F10"))
        self.actionRerun_step.setEnabled(False)
        icon = QIcon()
        icon.addPixmap(QPixmap(icon_prefix() + "/cycle.png"))
        self.actionRerun_step.setIcon(icon)
        self.actionRerun_step.triggered.connect(self.runner.on_rerun_step)
        self.stepBar.addAction(self.actionStart_test)
        self.stepBar.addAction(self.actionStop_test)
        self.stepBar.addSeparator()
        self.actionDebugOutput.setChecked(prefs.settings.debug_output)
        self.stepBar.addAction(self.actionDebugOutput)
        for action, tip in (
            (self.actionStep_over, "Step over (F10)"),
            (self.actionStep_into, "Step into (F11)"),
            (self.actionStep_out, "Step out (Shift+F11)"),
            (self.actionRerun_step, "Re-run last step (Shift+F10)"),
        ):
            action.setToolTip(tip)
            self.stepBar.addAction(action)
        # The step actions belong to the debug mode: shown (and their
        # shortcuts active) only when Debug is checked.
        self._set_step_actions_visible(self.actionDebugOutput.isChecked())

        self.addToolBar(Qt.TopToolBarArea, self.stepBar)
        # Fires on undock and on re-dock after a drag, so every move ends
        # with a style refresh matching the final area.
        self.stepBar.topLevelChanged.connect(
            lambda _: self._update_step_bar_style())
        self._update_step_bar_style()

    def _build_view_menu(self):
        self.menuView.addAction(self.logDockWidget.toggleViewAction())
        self.menuView.addAction(self.DocDockWidget.toggleViewAction())
        self.menuView.addAction(self.itemDock.toggleViewAction())
        self.menuView.addAction(self.variablesDock.toggleViewAction())
        self.menuView.addAction(self.stepBar.toggleViewAction())
        self.menuView.addSeparator()
        reset = self.menuView.addAction("Reset layout")
        reset.triggered.connect(self._apply_default_layout)

    def _apply_default_layout(self):
        """Default arrangement: log right (~38% width); doc, item and
        variables tabbed below it, doc on top."""
        docks = (self.logDockWidget, self.DocDockWidget,
                 self.itemDock, self.variablesDock)
        for dock in docks:
            dock.setFloating(False)
            dock.show()
        self.addDockWidget(Qt.RightDockWidgetArea, self.logDockWidget)
        self.splitDockWidget(self.logDockWidget, self.DocDockWidget,
                             Qt.Vertical)
        self.tabifyDockWidget(self.DocDockWidget, self.itemDock)
        self.tabifyDockWidget(self.itemDock, self.variablesDock)
        self.DocDockWidget.raise_()
        self.resizeDocks([self.logDockWidget],
                         [int(self.width() * 0.38)], Qt.Horizontal)
        self.resizeDocks([self.logDockWidget, self.DocDockWidget],
                         [int(self.height() * 0.55),
                          int(self.height() * 0.35)], Qt.Vertical)
        self.stepBar.setVisible(True)

    @property
    def run_exit_code(self):
        return self.runner.run_exit_code

    # --- RunView implementation (driven by gui/run_presenter.py) ----------

    def apply_run_ui(self, state: RunUiState):
        running = state.running
        self.actionOpenTest.setEnabled(not running)
        self.actionExit.setEnabled(not running)
        self.actionPreferences.setEnabled(not running)
        self.actionRefresh_test.setEnabled(not running)
        self.actionSave_report.setEnabled(not running)
        # Show Results stays available during the run (log grows live).
        self.actionShow_Results.setEnabled(True)
        self.logSettingsBox.setEnabled(not running)
        self.actionStop_test.setEnabled(running)
        for action in (self.actionStep_over, self.actionStep_into,
                       self.actionStep_out, self.actionRerun_step):
            action.setEnabled(state.steps_enabled)
        if not running:
            self.actionStep_into.setEnabled(self.actionStart_test.isEnabled())
            if prefs.settings.show_checkboxes:
                self.checkSelect.setEnabled(True)
            self.checkFold.setEnabled(True)
        else:
            self.checkSelect.setDisabled(True)
            self.checkFold.setDisabled(True)

    def set_start_action(self, text, icon):
        if text is not None:
            self.actionStart_test.setText(text)
        ic = QIcon()
        ic.addPixmap(QPixmap(icon_prefix() + f"/{icon}.png"))
        self.actionStart_test.setIcon(ic)

    def set_status_light(self, color):
        self.buttBlink.setIcon({"green": self.iconBlinkGreen,
                                "red": self.iconBlinkRed,
                                "gray": self.iconBlinkGray}[color])

    def set_elapsed(self, text):
        self.label_runtime.setText(text)

    def append_log(self, text):
        self.textLog.appendPlainText(text)

    def clear_log(self):
        self.textLog.clear()

    def show_transient_message(self, text):
        self.statusBar().showMessage(text, 10000)

    def can_start(self):
        return self.actionStart_test.isEnabled()

    def test_file(self):
        return self.testFile

    def log_config(self):
        return (self.editLogFilePath.text(),
                self.buttLogFileSaved.isChecked())

    def set_log_file_name(self, path):
        self.logFileName = path

    def report_config(self):
        return (self.reportFileName, self.report_type, self.report_pattern)

    def attach_log_sink(self, handle):
        self.out_log.set(handle)

    def detach_log_sink(self):
        self.out_log.reset()

    def read_captured(self):
        return self.stream.read()

    def reset_run_marks(self):
        self.treeTests.clearGlobalSuccess()
        self.treeTests.clearAllStatus()

    def clear_current_marks(self):
        self.treeTests.clearHighlights()

    def run_succeeded(self):
        return self.treeTests.getGlobalSuccess()

    def close_window(self):
        self.on_actionExit_triggered()

    def _update_step_bar_style(self):
        """Top area: main-toolbar look (large icons + text). Left/right/
        bottom or floating: compact icon-only."""
        if (not self.stepBar.isFloating()
                and self.toolBarArea(self.stepBar) == Qt.TopToolBarArea):
            self.stepBar.setIconSize(self.toolBar.iconSize())
            self.stepBar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        else:
            self.stepBar.setIconSize(QSize(16, 16))
            self.stepBar.setToolButtonStyle(Qt.ToolButtonIconOnly)

    def _search_fields(self):
        fields = set()
        if self.cbSearchName.isChecked():
            fields.add("name")
        if self.cbSearchType.isChecked():
            fields.add("type")
        if self.cbSearchDoc.isChecked():
            fields.add("doc")
        return fields

    def _toggle_search(self):
        """Ctrl+F: open the find bar, or close it (clearing the highlight)."""
        if self.searchBar.isVisible():
            self._close_search()
        else:
            self._open_search()

    def _open_search(self):
        self.searchBar.setVisible(True)
        self.searchEdit.setFocus()
        self.searchEdit.selectAll()
        if self.searchEdit.text():
            self._do_search()

    def _do_search(self):
        if self.treeTests is None:
            return
        self._search_matches = self.treeTests.search(
            self.searchEdit.text(), self._search_fields()
        )
        self._search_idx = 0
        if self._search_matches:
            self._goto_match(0)
        else:
            self._update_search_count()

    def _update_search_count(self):
        n = len(self._search_matches)
        if n == 0:
            self.searchCount.setText(
                "0/0" if self.searchEdit.text().strip() else ""
            )
        else:
            self.searchCount.setText("{}/{}".format(self._search_idx + 1, n))

    def _goto_match(self, idx):
        if not self._search_matches:
            return
        self._search_idx = idx % len(self._search_matches)
        it = self._search_matches[self._search_idx]
        self.treeTests.scrollToItem(it)
        self.treeTests.setCurrentItem(it)
        self._update_search_count()

    def _search_next(self):
        if self._search_matches:
            self._goto_match(self._search_idx + 1)

    def _search_prev(self):
        if self._search_matches:
            self._goto_match(self._search_idx - 1)

    def _close_search(self):
        if self.treeTests is not None:
            self.treeTests.clear_search()
            self.treeTests.setFocus()
        self.searchBar.setVisible(False)
        self._search_matches = []

    def _reset_search(self):
        """New test file loaded: drop stale matches and hide the bar."""
        self._search_matches = []
        self._search_idx = 0
        if hasattr(self, "searchBar"):
            self.searchBar.setVisible(False)
            self.searchCount.setText("")

    # Tree states and log-file choice are stored per test file, one settings
    # key per file: two instances on different files never clobber each other.
    FileStatesMax = 20

    def _file_state_key(self, path):
        digest = hashlib.sha1(
            os.path.normcase(os.path.abspath(path)).encode()).hexdigest()
        return "itemstates." + digest[:12]

    def stash_file_state(self, test_file):
        entry = [os.path.normcase(os.path.abspath(test_file)), time.time(),
                 self.treeTests.getItemStates(),
                 self.editLogFilePath.text(),
                 self.buttLogFileSaved.isChecked()]
        prefs.settings.set_value(
            prefs.SettingsItem(self._file_state_key(test_file), list), entry)
        self._trim_file_states()

    def _trim_file_states(self):
        names = prefs.settings.option_names("itemstates.")
        if len(names) <= self.FileStatesMax:
            return

        def saved_at(name):
            entry = prefs.settings.value(prefs.SettingsItem(name, list), [])
            return entry[1] if len(entry) >= 2 else 0

        for name in sorted(names, key=saved_at)[:len(names) - self.FileStatesMax]:
            prefs.settings.remove_value(name)

    def restore_file_state(self):
        if self.testFile is None:
            return
        entry = prefs.settings.value(
            prefs.SettingsItem(self._file_state_key(self.testFile), list), [])
        if len(entry) < 5:
            return
        states, log_file, log_saved = entry[2], entry[3], entry[4]
        if not self._cli_log_file:
            self.editLogFilePath.setText(log_file)
            self.logFileName = log_file
            self.buttLogFileSaved.setChecked(bool(log_saved))
        if states:
            self.checkFold.setCheckState(Qt.PartiallyChecked)
            self.treeTests.restoreItemStates(
                states, self.test_service,
                apply_check=prefs.settings.show_checkboxes)

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
            prefs.SettingsItem("state", bytearray),
            bytearray(self.saveState(self.STATE_VERSION))
        )
        if self.testFile:
            self.stash_file_state(self.testFile)
        self.treeTests.saveSizes()
        prefs.settings.sync()

    def closeEvent(self, event):
        self.on_exiting()
        event.accept()

    def on_exiting(self):
        # closeEvent can fire more than once (runandclose paths call close()).
        if getattr(self, "_exited", False):
            return
        self._exited = True
        try:
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

    @Slot()
    def on_actionStop_test_triggered(self):
        self.runner.on_stop_test()

    @Slot()
    def on_actionStep_over_triggered(self):
        self.runner.on_step_over()

    @Slot()
    def on_actionStep_into_triggered(self):
        self.runner.on_step_into()

    @Slot()
    def on_actionStep_out_triggered(self):
        self.runner.on_step_out()

    def on_paused(self):
        self.runner.on_paused()

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
            if self.pref_win.isChanged(prefs.settings.SettingsShowCheckboxes):
                self.show_checkboxes()
            if self.pref_win.isChanged(prefs.settings.SettingsDblClickEnabled):
                if prefs.settings.dbl_click_enabled:
                    self.treeTests.itemDoubleClicked.connect(self.on_testItemDblClicked)
                else:
                    self.treeTests.itemDoubleClicked.disconnect()
            if self.pref_win.isChanged(prefs.settings.SettingsShowTimeColumn):
                self.treeTests.set_time_column_visible(
                    prefs.settings.show_time_column)
            if self.pref_win.isChanged(prefs.settings.SettingsLogFont):
                self.prefs_apply_font()
            if self.pref_win.isChanged(prefs.settings.SettingsLogFontSize):
                self.prefs_apply_font_size()

    def on_testTreeContextMenu(self, pos):
        """Per-item debug actions. Options that do not apply are shown
        disabled so they stay discoverable."""
        item = self.treeTests.itemAt(pos)
        if item is None or self.test_service is None:
            return
        is_py_func = item.test_type == cst.TYPE_PY_FUNCTION.item_name
        menu = QMenu(self.treeTests)
        attach = menu.addAction("Wait for IDE debugger (py_func)")
        attach.setCheckable(True)
        attach.setChecked(is_py_func and item.isDebugAttach())
        attach.setEnabled(is_py_func)
        condition = menu.addAction("Breakpoint condition…")
        condition.setEnabled(not item._no_breakpoint)
        jump = menu.addAction("Jump to this item")
        jump.setEnabled(self.runner.state == TestState.PAUSED
                        and not item._is_skipped
                        and not self._in_parallel(item))
        chosen = menu.exec(self.treeTests.viewport().mapToGlobal(pos))
        if chosen is attach:
            enabled = attach.isChecked()
            self.test_service.set_debug_attach(item.id, enabled)
            item.setDebugAttachState(enabled)
        elif chosen is condition:
            self._edit_breakpoint_condition(item)
        elif chosen is jump:
            try:
                self.test_service.jump_to(item.id)
            except ETUMRuntimeError as e:
                self.statusBar().showMessage(str(e), 10000)

    def _in_parallel(self, item):
        p = item
        while p is not None:
            if p.test_type in (cst.TYPE_PARALLEL.item_name,
                               cst.TYPE_PARALLEL_BRANCH.item_name):
                return True
            p = p.parent()
        return False

    def _edit_breakpoint_condition(self, item):
        dlg = QDialog(self)
        dlg.setWindowTitle("Breakpoint condition")
        layout = QVBoxLayout(dlg)
        row = QHBoxLayout()
        row.addWidget(QLabel("Pause only when true:"))
        edit = QLineEdit(getattr(item, "_bp_condition", None) or "")
        edit.setPlaceholderText("$(var) == 3")
        edit.setMinimumWidth(280)
        row.addWidget(edit, 1)
        row.addWidget(expression_info_button(
            dlg, extra="<br>The run pauses on the item only when the result "
                       "is true. Empty: unconditional breakpoint."))
        layout.addLayout(row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        edit.setFocus()
        if dlg.exec() != QDialog.Accepted:
            return
        text = edit.text().strip()
        if text:
            item.setBreakpointState(True, text)
            self.test_service.add_breakpoint(item.id, condition=text)
        elif item.isBreakpoint():
            # Emptied condition: back to a plain breakpoint.
            item.setBreakpointState(True)
            self.test_service.add_breakpoint(item.id)

    def _set_step_actions_visible(self, visible):
        for action in (self.actionStep_over, self.actionStep_into,
                       self.actionStep_out, self.actionRerun_step):
            action.setVisible(visible)

    @Slot(bool)
    def on_actionDebugOutput_toggled(self, checked):
        prefs.settings.debug_output = checked
        self._set_step_actions_visible(checked)
        if self.test_service is not None:
            self.test_service.set_gd_var("test_debug", bool(checked))

    def sync_debug_output_action(self, gd_vars):
        """Show the effective test_debug value; the preference is unchanged."""
        effective = bool(gd_vars.get("test_debug", False))
        if effective != self.actionDebugOutput.isChecked():
            self.actionDebugOutput.blockSignals(True)
            self.actionDebugOutput.setChecked(effective)
            self.actionDebugOutput.blockSignals(False)
            self._set_step_actions_visible(effective)

    @Slot()
    def on_actionRefresh_test_triggered(self):
        target = self.testFile or getattr(self, "_attempted_file", None)
        if target:
            self.file_manager.reload(target)

    @Slot()
    def on_actionSave_report_triggered(self):
        if self.testFile:
            initialPath = os.path.dirname(self.testFile)
        else:
            initialPath = None
        fileName, _ = QFileDialog.getSaveFileName(
            self, "Path to Log file", initialPath, "Log Files (*.log);;All Files (*)",
            options=file_dialog.options(),
        )
        if fileName:
            shutil.copy(self.logFileName, fileName)

    @Slot()
    def on_actionShow_Results_triggered(self):
        s = sys.platform
        self.statusBar().showMessage(
            "Opening the logfile (" + s + "): " + self.logFileName, 100000
        )
        if not bins.host_open_path(self.logFileName):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.logFileName))

    @Slot()
    def on_actionHelp_triggered(self):
        self.webbrowser_open()

    def webbrowser_open(self):
        def open_browser_thread():
            webbrowser.open(
                "https://github.com/testium-HIL/testium/blob/main/doc/manual/testium_manual.pdf",
                new=2,
                autoraise=True,
            )
        thread = Thread(target=open_browser_thread)
        thread.daemon = True
        thread.start()

    @Slot()
    def on_actionTestInformation_triggered(self):
        self._toggle_panel(self.itemDock)

    def on_actionVariables_triggered(self):
        self._toggle_panel(self.variablesDock)

    @staticmethod
    def _toggle_panel(dock):
        # Hidden or tabbed behind (not visible for Qt): bring it to the
        # front; visible on top: hide it.
        if dock.isVisible():
            dock.hide()
        else:
            dock.show()
            dock.raise_()

    def on_buttLogFilePath_clicked(self):
        if self.editLogFilePath.text() != "":
            initialPath = os.path.dirname(self.editLogFilePath.text())
        elif self.testFile:
            initialPath = os.path.dirname(self.testFile)
        else:
            initialPath = None
        fileName, _ = QFileDialog.getSaveFileName(
            self, "Path to log file", initialPath, "Log Files (*.log);;All Files (*)",
            options=file_dialog.options(),
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
            self.itemDock.show_item(items[0])

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
                self._open_in_editor(self.logFileName, ln + 1)

    def _open_in_editor(self, path, line):
        """Open path at line via the configured editor template ({file}/{line}).
        Empty template or failure falls back to opening the file without line."""
        tmpl = prefs.settings.editor_cmd
        if tmpl:
            try:
                argv = [p.format(file=path, line=line) for p in shlex.split(tmpl)]
                subprocess.Popen(bins.host_console_command(argv, os.path.dirname(path) or "."))
                return
            except (KeyError, ValueError, IndexError, OSError):
                pass
        if not bins.host_open_path(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def on_spacePressed(self):
        item = self.treeTests.currentItem()
        add_breakpoint = item.setBreakpoint()
        if add_breakpoint:
            self.test_service.add_breakpoint(item.id)
        else:
            self.test_service.del_breakpoint(item.id)

    def on_F1Pressed(self):
        item = self.treeTests.currentItem()
        if item is not None:
            self.itemDock.show_item(item)
        self.variablesDock.show()
        self.variablesDock.raise_()
        self.variablesDock.filter_edit.setFocus()

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

    def on_logToBeAppended(self, m):
        self.textLog.moveCursor(QtGui.QTextCursor.End)
        self.textLog.insertPlainText(m)


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
    # Application identity so desktop shells (GNOME, ...) show the testium
    # icon in the task bar / dock instead of a generic one. On Wayland this
    # sets the surface app_id; on X11/XWayland it sets WM_CLASS, so the window
    # stops inheriting the launcher's class (e.g. "python3" under the AppImage,
    # which is what GNOME was keying the wrong icon off) and the window icon
    # below is used as the fallback. In Flatpak the id must be the Flatpak app
    # id so it matches the installed desktop file.
    app.setApplicationName("Testium")
    app.setApplicationDisplayName("Testium")
    app.setDesktopFileName(os.environ.get("FLATPAK_ID", "testium"))
    app.setWindowIcon(QIcon(u":/black/testium_logo.png"))
    # On native Wayland the task-bar icon comes from an installed desktop file
    # matched to the app_id, not from setWindowIcon(). Flatpak ships its own;
    # for the other Linux channels drop an idempotent one under ~/.local/share.
    # Windows / macOS use the window icon set above, so this is Linux-only.
    if sys.platform.startswith("linux") and not os.environ.get("FLATPAK_ID"):
        from main_win.desktop_integration import ensure_desktop_entry
        ensure_desktop_entry()
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
