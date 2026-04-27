import os
from pathlib import Path
import datetime
from socket import gethostname
import ast
import yaml
import copy

from interpreter.utils.constants import TestItemType as cst
import libs.testium as tm
import interpreter.utils.globdict as globdict
import interpreter.utils.settings as prefs
from interpreter.utils.paths import testium_path
from interpreter.utils.yaml_load import yaml_load
from interpreter.utils import clear_recursively
from lib.tum_except import ETUMSyntaxError
from interpreter.utils.params import expanse, eval_func_init
from interpreter.utils.eval import evaluate
from interpreter.utils.version import (
    get_version,
    get_testium_version,
    get_modifications,
)

from interpreter.test_items.test_item import TestItem
from interpreter.test_items.test_item_sleep import TestItemSleep
from interpreter.test_items.test_item_unittest import TestItemUnittestFile
from interpreter.test_items.test_item_cycle import TestItemCycle
from interpreter.test_items.test_item_runtime_plot import TestItemPlot
from interpreter.test_items.test_item_group import TestItemGroup
from interpreter.test_items.test_item_git import TestItemGit
from interpreter.test_items.test_item_py_func import TestItemPyFunc
from interpreter.test_items.test_item_lua_func import TestItemLuaFunc
from interpreter.test_items.test_item_let import TestItemLet
from interpreter.test_items.test_item_check import TestItemCheckValue
from interpreter.test_items.test_item_json_rpc import TestItemJSON_RPC
from interpreter.test_items.test_item_value_dialog import TestItemValueDialog
from interpreter.test_items.test_item_note_dialog import TestItemNoteDialog
from interpreter.test_items.test_item_image_dialog import TestItemImageDialog
from interpreter.test_items.test_item_msg_dialog import TestItemMsgDialog
from interpreter.test_items.test_item_question_dialog import TestItemQuestionDialog
from interpreter.test_items.test_item_tested_references import TestItemTestedRefsDialog
from interpreter.test_items.test_item_choices_dialog import TestItemChoicesDialog
from interpreter.test_items.test_item_console import TestItemConsole
from interpreter.test_items.test_item_run import TestItemRun
from interpreter.test_items.test_item_report import TestItemReport


def _constants_init():
    cst.TYPE_CONSOLE.item_class = TestItemConsole
    cst.TYPE_CYCLE.item_class = TestItemCycle
    cst.TYPE_PY_FUNCTION.item_class = TestItemPyFunc
    cst.TYPE_LUA_FUNCTION.item_class = TestItemLuaFunc
    cst.TYPE_GIT.item_class = TestItemGit
    cst.TYPE_GRAPH.item_class = TestItemPlot
    cst.TYPE_GROUP.item_class = TestItemGroup
    cst.TYPE_IMAGE_DLG.item_class = TestItemImageDialog
    cst.TYPE_JSON_RPC.item_class = TestItemJSON_RPC
    cst.TYPE_LET.item_class = TestItemLet
    cst.TYPE_CHECK.item_class = TestItemCheckValue
    cst.TYPE_MESSAGE_DLG.item_class = TestItemMsgDialog
    cst.TYPE_NOTE_DLG.item_class = TestItemNoteDialog
    cst.TYPE_QUESTION_DLG.item_class = TestItemQuestionDialog
    cst.TYPE_REFERENCE_DLG.item_class = TestItemTestedRefsDialog
    cst.TYPE_CHOICES_DLG.item_class = TestItemChoicesDialog
    cst.TYPE_REPORT.item_class = TestItemReport
    cst.TYPE_ROOT.item_class = TestItem
    cst.TYPE_RUN.item_class = TestItemRun
    cst.TYPE_SLEEP.item_class = TestItemSleep
    cst.TYPE_UNITTEST.item_class = TestItemUnittestFile
    cst.TYPE_VALUE_DLG.item_class = TestItemValueDialog


def locate_report_file(rep_file):
    # report file name treatment
    if rep_file != "":
        if not os.path.isabs(rep_file):
            rep_file = os.path.join(os.getcwd(), rep_file)
            rep_file = os.path.normpath(rep_file)
        if not os.path.exists(os.path.dirname(rep_file)):
            os.makedirs(os.path.dirname(rep_file))

    return rep_file


def yamltodict(param_file, silent=True):
    # load of the file
    with open(param_file, "r") as fd:
        dp = yaml_load(fd, param_file, yaml.Loader)

    if dp is None:
        tm.print_info(f"The YAML file '{param_file}' is empty.")
        return

    # update the global dict with raw data
    globdict.global_dict.update(dp)

    # Apply variables expansion
    for i in range(10):
        for key, val in dp.items():
            val = expanse(val)
            dp.update({key: val})

    if not silent:
        if not tm.debug_enabled():
            tm.print_info(f'"{param_file}" loaded.')
        else:
            tm.print_debug(f'"{param_file}" loading:')
            for k, v in dp.items():
                tm.print_debug(f"  {k}: {v}")
            tm.print_debug(f"done.")

    # Finalize the global dict update
    globdict.global_dict.update(dp)


def _feed_gd_with_params(param_file, silent=True):
    test_dir = tm.gd("test_directory")
    # param files pre-processing
    files = []
    for p in param_file:
        if isinstance(p, str):
            files.append(p)
        elif isinstance(p, list):
            for pp in p:
                files.append(pp)
    for p in files:
        if p is None:
            continue
        if not isinstance(p, str):
            raise ETUMSyntaxError(f'Parameter file "{p}" not a file path.')
        p = expanse(p)
        pf = p
        if not os.path.isabs(pf):
            pf = os.path.normpath(os.path.join(test_dir, pf))
        if not os.path.isfile(pf):
            raise ETUMSyntaxError(f'Parameter file "{pf}" not found')

        ext = os.path.splitext(pf)[1]
        if (ext == ".yaml") or (ext == ".yml"):
            yamltodict(pf, silent)
        else:
            raise ETUMSyntaxError('config files must be "*.yaml" or "*.yml"')


def set_standard_gd_keys(test_name, test_dir, test_file, config_files):
    tm.setgd("testium_version", get_testium_version())
    tm.setgd("testium_path", testium_path())
    tm.setgd("test_name", test_name)
    tm.setgd("test_directory", test_dir)
    tm.setgd("test_main_file", test_file)
    tm.setgd("config_files", config_files)
    tm.setgd("host_name", gethostname())
    tm.setgd("home", str(Path.home()))
    tm.setgd("os", tm.OS())


def env_init():
    if not hasattr(prefs, "settings"):
        prefs.init()
    eval_func_init(evaluate)
    _constants_init()


def update_global(config_files, defines, gui_defaults, silent=False):
    """Global dict updated with the content of the config file and a dict provided.
    this function returns the resulting dict.
    """
    # GUI preferences applied first
    for k, v in gui_defaults.items():
        try:
            val = ast.literal_eval(v)
        except:
            val = v
        tm.setgd(k, val)

    # Then command line defines
    for k, v in defines.items():
        try:
            val = ast.literal_eval(v)
        except:
            val = v
        tm.setgd(k, val)

    # Then the configuration files
    # load global dic before test item
    _feed_gd_with_params(config_files, silent)

    # Re-apply command line defines to ensure it has not been
    # overloaded by the configuration files
    for k, v in defines.items():
        try:
            val = ast.literal_eval(v)
        except:
            val = v

        conf_val = tm.gd(k)
        if val != conf_val:
            if not silent:
                tm.print_info(
                    f'Variable $({k}) overloaded by command line arg --> "{val}".'
                )
            tm.setgd(k, val)

    return globdict.global_dict


def prepare_global():
    # Global dict setup
    globdict.cleargd()


def backup_gd():
    return copy.deepcopy(globdict.global_dict)


def restore_gd(dict):
    clear_recursively(globdict.global_dict)
    globdict.global_dict.update(dict)


def test_run_init():
    tm.init_timestamp()

    test_dir = tm.gd("test_directory")
    tm.setgd("test_version", get_version(test_dir))
    tm.setgd("test_modifs", get_modifications(test_dir))

    start_test_date = datetime.datetime.now()
    tm.setgd("start_test_date", start_test_date)
    tm.setgd("testrun_date", start_test_date.strftime("%Y-%m-%d"))
    tm.setgd("testrun_time", start_test_date.strftime("%H:%M:%S"))


def test_run_header():
    tool_version = tm.gd("testium_version")
    test_file = tm.gd("test_main_file", "")
    has_test_file = tm.gd("test_main_file") != ""

    s = ""
    s += (80 * "=") + "\n"
    s += "====== Test overview" + "\n"
    s += (80 * "=") + "\n"
    if has_test_file:
        s += ("Executed test file              : " + test_file) + "\n"
    for cf in tm.gd("config_files"):
        s += ("With param file                 : {}".format(cf)) + "\n"
    s += (
        "Test started                    : "
        + tm.gd("testrun_date")
        + " "
        + tm.gd("testrun_time")
    ) + "\n"

    s += (80 * "=") + "\n"
    s += ("====== Test configuration") + "\n"
    s += (80 * "=") + "\n"
    s += ("Test executed with testium      : " + tool_version.splitlines()[0]) + "\n"
    for l in tool_version.splitlines()[1:]:
        s += (32 * " " + ": " + l) + "\n"
    s += " \n"
    if has_test_file:
        test_version = tm.gd("test_version")
        test_modifs = tm.gd("test_modifs")
        s += (
            "Test scripts revision           : " + test_version.splitlines()[0]
        ) + "\n"

        for l in test_version.splitlines()[1:]:
            s += (32 * " " + ": " + l) + "\n"
        for l in test_modifs.splitlines():
            s += ("  " + l) + "\n"
    return s
