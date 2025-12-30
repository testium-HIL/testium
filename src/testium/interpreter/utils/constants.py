
from enum import Enum

class TestItemEnum():
    def __init__(self, cmd, name, item_class=None) -> None:
        self.name = name
        self.cmd = cmd
        self.item_class = item_class

class TestItemType(Enum):
    TYPE_UNITTEST_FILE      = TestItemEnum("unittest_file", "unittest file")
    TYPE_UNITTEST_STEP      = TestItemEnum("unittest_step", "unittest step")
    TYPE_CONSOLE            = TestItemEnum("console", "Console")
    TYPE_CONSOLE_ACTION     = TestItemEnum("console_action", "Console action")
    TYPE_CYCLE              = TestItemEnum("loop", "Cycle")
    TYPE_PY_FUNCTION        = TestItemEnum("py_func", "python Function")
    TYPE_LUA_FUNCTION       = TestItemEnum("lua_func", "lua Function")
    TYPE_REPORT             = TestItemEnum("report", "Report")
    TYPE_GIT                = TestItemEnum("git", "git repository")
    TYPE_GRAPH              = TestItemEnum("plot", "Runtime plot")
    TYPE_GRAPH_ACTION       = TestItemEnum("plot_action", "Runtime plot action")
    TYPE_GROUP              = TestItemEnum("group", "Group")
    TYPE_IMAGE_DLG          = TestItemEnum("dialog_image", "Image Dialog")
    TYPE_MESSAGE_DLG        = TestItemEnum("dialog_message", "Message Dialog")
    TYPE_LET                = TestItemEnum("let", "Let")
    TYPE_CHECK              = TestItemEnum("check", "Check value")
    TYPE_NOTE_DLG           = TestItemEnum("dialog_note", "Note Dialog")
    TYPE_QUESTION_DLG       = TestItemEnum("dialog_question", "Question Dialog")
    TYPE_SLEEP              = TestItemEnum("sleep", "Sleep")
    TYPE_REFERENCE_DLG      = TestItemEnum("dialog_references", "References Dialog")
    TYPE_VALUE_DLG          = TestItemEnum("dialog_value", "Value Dialog")
    TYPE_CHOICES_DLG        = TestItemEnum("dialog_choices", "Choices Dialog")
    TYPE_RUN                = TestItemEnum("run", "Run tum")
    TYPE_JSON_RPC           = TestItemEnum("json_rpc", "JSON-RPC")
    TYPE_JSON_RPC_ACTION    = TestItemEnum("json_rpc_action", "JSON-RPC action")
    TYPE_ROOT               = TestItemEnum("default", "default")

    @staticmethod
    def list():
        return list(map(lambda c: c.value, TestItemType))

    @property
    def item_name(self):
        return self.value.name

    @property
    def item_cmd(self):
        return self.value.cmd

    @property
    def item_class(self):
        return self.value.item_class

    @item_class.setter
    def item_class(self, c):
        self.value.item_class = c

    def __str__(self):
        return self.value.name

TEST_TYPE_LIST = [e for e in TestItemType]

REP_TYPE_SQLITE     = "sqlite"
REP_TYPE_JUNIT      = "junit"
REP_TYPE_JSON       = "json"
REP_TYPE_HTML       = "html"
REP_TYPE_TEXT       = "text"

REP_TYPES = [
        REP_TYPE_SQLITE,
        REP_TYPE_JUNIT,
        REP_TYPE_JSON,
        REP_TYPE_HTML,
        REP_TYPE_TEXT,
    ]

# Report related constants

DB_REPORT_VERSION = "report_version"
DB_TEST_FILE = "test_file"
DB_TEST_SET_NAME = "test_name"
DB_TEST_SET_RESULT = "test_result"
DB_TEST_REVISION = "test_revision"
DB_SEQUENCER_VERSION = "testium_version"
DB_TESTRUN_DATE = "testrun_date"
DB_TESTRUN_TIME = "testrun_time"
DB_TEST_SET_DURATION = "test_duration"

DB_HEADER_FIELDS = [
    DB_REPORT_VERSION,
    DB_TEST_FILE,
    DB_TEST_SET_NAME,
    DB_TEST_SET_RESULT,
    DB_TEST_REVISION,
    DB_SEQUENCER_VERSION,
    DB_TESTRUN_DATE,
    DB_TESTRUN_TIME,
    DB_TEST_SET_DURATION,
]

DB_TEST_TIMESTAMP_START = "timestamp_start"
DB_TEST_ID = "test_id"
DB_TEST_PARENT_ID = "parent_id"
DB_TEST_NAME = "test_name"
DB_TEST_TYPE = "test_type"
DB_TEST_KEY = "report_key"
DB_TEST_RESULT = "result"
DB_TEST_MESSAGE = "message"
DB_TEST_DURATION = "duration"
DB_TEST_DATA = "data"
DB_TEST_LEVEL = "level"
DB_TEST_LOG = "log"

DB_TEST_FIELDS = [
    DB_TEST_TIMESTAMP_START,
    DB_TEST_ID,
    DB_TEST_PARENT_ID,
    DB_TEST_NAME,
    DB_TEST_TYPE,
    DB_TEST_KEY,
    DB_TEST_RESULT,
    DB_TEST_MESSAGE,
    DB_TEST_DURATION,
    DB_TEST_DATA,
    DB_TEST_LEVEL,
    DB_TEST_LOG,
]

ICON_THEMES_PREFIX = [
    ":/color",
    ":/black"
]

FOLDED_CHAR         = "."