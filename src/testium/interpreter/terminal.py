try:
    import readline
except:
    pass
from cmd import Cmd
import os
import sys
from yaml import load, Loader
import functools
import platform
import types
import inspect

# test modules
from interpreter.utils.test_init import (
    env_init, prepare_global, set_standard_gd_keys,
    update_global, test_run_init, test_run_header, load_test)
from interpreter.utils.globdict import (global_dict)
import libs.testium as tm
from interpreter.utils.constants import TestItemType as cst
from interpreter.test_report.test_report import TestReport


class FakeQueue:
    def put(self, arg):
        pass


def func(self, args):
    if not args.startswith("{"):
        args = "{"+args+"}"
    y = load(args, Loader)
    obj = self.current_item(y, status_queue=FakeQueue())
    obj.report = self.report
    res = obj.execute()
    if not (res.value is None):
        print('result : {}'.format(res.value))
    print(res.test_result)


class Terminal(Cmd):
    SUPPORTED_TESTS = [
        cst.TYPE_SLEEP,
        cst.TYPE_LET,
        cst.TYPE_PY_FUNCTION,
        cst.TYPE_LUA_FUNCTION,
        cst.TYPE_CONSOLE,
        cst.TYPE_IMAGE_DLG,
        cst.TYPE_MESSAGE_DLG,
        cst.TYPE_QUESTION_DLG,
        cst.TYPE_VALUE_DLG,
    ]

    SUPPORTED_GROUPS = [
        cst.TYPE_GROUP,
        cst.TYPE_CYCLE
    ]

    def __init__(self, working_dir, config_files, defines, no_color, text_mode=False):
        super().__init__()
        self.working_dir = working_dir
        self.config_files = config_files
        self.current_item = None
        report = TestReport(None)
        self.report = report

        env_init()
        prepare_global()
        # Define the builtin variables
        set_standard_gd_keys("Unnamed", self.working_dir, '', config_files)
        update_global([], defines)
        if text_mode:
            tm.setgd("_text_mode", True)

        # creation of the functions
        for tst in self.SUPPORTED_TESTS:
            meth_name = "do_" + tst.item_cmd
            # copy of the function
            f = types.FunctionType(func.__code__, func.__globals__, name=meth_name,
                                   argdefs=func.__defaults__,
                                   closure=func.__closure__)
            f = functools.update_wrapper(f, func)
            f.__kwdefaults__ = func.__kwdefaults__
            f.__doc__ = tst.item_class.__doc__
            setattr(self, meth_name, types.MethodType(f, self))

        test_run_init()
        self.prompt = "(testium)~ "

        # display header
        print(test_run_header())
        # redirect output

        if 'Linux' in platform.system() and not no_color:
            from lib.stdout_redirect import stdio_redir
            try:
                from interpreter.utils.termlog import TermLog
                stdio_redir.redirect(TermLog(sys.stdout))
            except ModuleNotFoundError:
                tm.print_info('Colored console not supported by the system.' +
                      ' If you want it, please install colorama module')

    def precmd(self, line: str) -> str:
        c = line.split(" ", 1)[0].strip()
        self.current_item = None
        for tst in self.SUPPORTED_TESTS:
            if c == tst.item_cmd:
                self.current_item = tst.item_class
                break
        return line

    def load_test_recursively(self, tree_parent, parent_seq, status_queue):
        try:
            parent_seq_name = parent_seq['name']
        except KeyError:
            parent_seq['name'] = "sequence"
        except TypeError:
            raise Exception("Syntax error in an item of type {} which is a child of {}".format(
                tree_parent.type(), tree_parent.parent().name()))
        try:
            parent_seq_actions = parent_seq['steps']
        except KeyError:
            raise Exception(' No action list found for "%s" sequence'
                            % (parent_seq_name))
        # if action is a dictionary , we assume it is a single action
        # that has not been nested in a list, so do it
        if isinstance(parent_seq_actions, (dict)):
            parent_seq_actions = [parent_seq_actions]
        if not isinstance(parent_seq_actions, (list, tuple)):
            raise Exception('Actions list not valid.')
        # first we merged to the same level 'sequence dict entries and list within the list
        counter = 0
        test_dir = tm.gd('test_directory')
        while (counter < len(parent_seq_actions)):
            action = parent_seq_actions[counter]
            # if action is a list raise up to the the same level,
            # ie insert action element into the parent_seq_actions
            if isinstance(action, (list, tuple)):
                parent_seq_actions[counter:counter+1] = action
                continue
            # if action is a NoneType skip and continue
            # (when pointing to an unused alias for instance)
            if action is None:
                counter += 1
                continue
            # if action is a sequence we insert its entry into the action list
            if 'sequence' in action:
                parent_seq_actions[counter:counter+1] = action['sequence']
                continue
            else:
                executed = False
                for it in [*self.SUPPORTED_TESTS, *self.SUPPORTED_GROUPS]:
                    if it.item_cmd in action:
                        executed = True
                        item = (it.item_class)(action[it.item_cmd],
                                               tree_parent,
                                               status_queue)
                        # check for sequence type:
                        if it.item_cmd == cst.TYPE_UNITTEST.item_cmd:
                            item.setTestDir(test_dir)
                            item.load()
                        elif ((it.item_cmd == cst.TYPE_CYCLE.item_cmd) or
                              (it.item_cmd == cst.TYPE_GROUP.item_cmd)):
                            self.load_test_recursively(
                                item, action[it.item_cmd], status_queue)

                if not executed:
                    raise Exception('action type is not known "{}"'.format(
                        list(action.keys())[0]))

            counter += 1

    def __setReportRecursively(self, parent):
        for i in range(parent.childCount()):
            parent.child(i).report = self.report
            self.__setReportRecursively(parent.child(i))

    def setReport(self, root_item):
        root_item.report = self.report
        self.__setReportRecursively(root_item)

    def get_names(self):
        memb = inspect.getmembers(self)
        return [n[0] for n in memb if (inspect.ismethod(n[1]) and n[0].startswith("do_"))]

    def do_load(self, args):
        """load function.

This function loads and executes a testium sub-script.

The loaded sequence can't be a main testium script ("testium -b" option is
defined for such a usage).

Accepted files are with extension "*.tum".

usage:
    load path/to/my/sequence.tum
"""
        file = args.strip()
        suff = file[-4:]
        if not suff in ['.tum']:
            raise Exception('Wrong input file extension')

        if not (os.path.exists(file) and os.path.isfile(file)):
            raise Exception(
                '"{}" does not exist or is not a file.'.format(file))

        d, _ = load_test(file)
        if not isinstance(d, list):
            raise Exception(
                "The file root object must be a list. A \"main\" tum can't be loaded from here (use batch mode instead).")

        if (len(d) == 1) and isinstance(d[0], dict) and (not d[0].get('sequence', None) is None):
            d = d[0]['sequence']

        sq = FakeQueue()
        root_item = (cst.TYPE_ROOT.item_class)(
            dict_item={'steps': d}, status_queue=sq)
        self.load_test_recursively(root_item, {'steps': d}, sq)
        self.setReport(root_item)
        res = root_item.execute()
        if not (res.value is None):
            print('"{}" execution overall result: {}'.format(file, res.value))
        print(res.test_result)

    def do_gd(self, args):
        """Variables lists and values.

usage:
    gd
    gd home
"""
        if args != '':
            res = tm.gd(args, None)
            if res is None:
                raise Exception(
                    'the variable: "{}" has not been found.'.format(args))
            print(res)
            return

        for k in global_dict.keys():
            print('{}: {}'.format(str(k), str(global_dict[k])))

    def do_quit(self, args):
        '''Quit the application.'''
        raise Exception('quit')
