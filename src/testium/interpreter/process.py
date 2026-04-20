import os
from multiprocessing import Process, Queue, Pipe
from queue import Empty
from threading import Thread
from time import sleep
import copy

from lib.string_queue import StringQueue
from lib.tum_except import print_exception, ETUMRuntimeError, ETUMSyntaxError
import libs.testium as tm
import interpreter.utils.globdict as globdict
from interpreter.utils.params import expanse
from interpreter.utils.test_ctrl import TestSetController
from interpreter.utils.test_init import (
    env_init,
    prepare_global,
    update_global,
    set_standard_gd_keys,
    test_run_init,
    test_run_header,
    locate_report_file,
    backup_gd,
    restore_gd,
)
from interpreter.utils.constants import TestItemType as cst_type
from interpreter.test_set import TestSet
from interpreter.utils.include import TUMLoader, TUMLoaderNoIncludes, TUMLoaderRawIncludes
from lib.stdout_redirect import stdio_redir
from interpreter.utils.template import template_to_test
from interpreter.utils.yaml_load import yaml_load
from interpreter.utils.py_eval import eval_process_init
from interpreter.utils.api_srv import api_request


class TestProcess(Process):
    def __init__(
        self,
        file_name,
        status_queue: Queue,
        tst_control: TestSetController,
        config_files,
        defines,
        gui_defaults={},
    ) -> None:
        super().__init__()
        self.__fname = file_name
        self.__squeue = status_queue
        self.__tctrl = tst_control
        self.__cfgf = config_files
        self.__defs = defines
        self.__gui_defaults = gui_defaults  # default values coming from GUI prefs
        self.__exec = False
        self.__loaded = False
        self.__closed = False
        self.__pconn = self.redirect_stdout()


    def _check_test_dict(self, test_dict):
        if not isinstance(test_dict, dict):
            raise ETUMSyntaxError(
                "The tum file has a major problem. Please check the documentation for syntax.")
        if not 'main' in test_dict.keys():
            raise ETUMSyntaxError(
                "The tum file has a major problem. The 'main' section could not be found.")

    def _locate_config_files(self, test_dir, config_files, silent=False):
        ret = []
        pf = []
        if len(config_files) == 0:
            for p in ['param.yaml', 'param.yml']:
                param_filename = os.path.join(test_dir, p)
                if os.path.exists(param_filename):
                    pf.append(param_filename)
                    if not silent:
                        tm.print_info(f"Configuration file loaded: {p}.")
                else:
                    if not silent:
                        tm.print_info(f"Default param file \"{p}\" does not exist.")
        else:
            pf = config_files

        for p in pf:
            ret.append(p)
        return ret


    def _config_files_from_test(self, test_dict, config_files=None):
        test_dir = tm.gd('test_directory')
        pf = []
        if isinstance(config_files, list) and len(config_files) == 0:
            param_filename = test_dict.get('config_file', None)
            if param_filename is None:
                param_node = test_dict.get('param_file', None)
                if param_node is not None:
                    if isinstance(param_node, dict):
                        p = param_node.get('file_name', None)
                        if p is not None:
                            param_filename = p
                        else:
                            param_filename = param_node
                    else:
                        param_filename = param_node
            if param_filename is None:
                pf = self._locate_config_files(test_dir, [])
            elif isinstance(param_filename, str):
                pf.append(param_filename)
            elif isinstance(param_filename, (list)):
                pf = []
                for p in param_filename:
                    if isinstance(p, list):
                        for pp in p:
                            pf.append(pp)
                    elif p is not None:
                        pf.append(p)
            else:
                raise ETUMSyntaxError(
                    'Unrecognized tum "param_file" : {}'.format(param_filename))
        elif isinstance(config_files, list):
            pf = config_files
        elif isinstance(config_files, str):
            pf = [config_files]
        else:
            raise ETUMSyntaxError(
                'Unrecognized config_files parameter : {}'.format(config_files))
        return pf


    def _load_test_dict(self, test_file, variables: dict, no_include: bool = False, raw_include: bool = False):
        loader = TUMLoader
        loader = TUMLoaderRawIncludes if raw_include else loader
        loader = TUMLoaderNoIncludes if no_include else loader

        # Jinja template processing
        tmpf = template_to_test(test_file, variables)
        try:
            d = yaml_load(tmpf, test_file, loader)
        finally:
            tmpf.close()

        return d


    def _load_initial_params(self, test_dir):
        # First step: populate config files without includes considered
        test_dict = self._load_test_dict(self.__fname, {}, no_include=True)
        self._check_test_dict(test_dict)
        prepare_global()

        # Define the global builtin variables
        set_standard_gd_keys(test_dict["main"].get(
            "name", "Unnamed"), test_dir, self.__fname, self.__cfgf)

        # Include the content of the first config files into glob dict
        old_pfs = self._config_files_from_test(test_dict, self.__cfgf)

        # Variables updated
        gd = update_global(old_pfs, self.__defs, self.__gui_defaults, silent=True)
        return old_pfs, gd


    def _load_test(self, init_param_files, glob_variables):

        old_pfs = init_param_files
        gd = glob_variables

        while True:
            # Loop to check param files until all param files are identified
            test_dict = self._load_test_dict(self.__fname, gd, raw_include=True)
            new_pfs = self._config_files_from_test(test_dict, self.__cfgf)

            # Check if things have changed since previous evaluation of
            # config files
            new_stuff = False
            if len(old_pfs) != len(new_pfs):
                new_stuff = True

            if not new_stuff:
                for i in range(len(old_pfs)):
                    if old_pfs[i] != new_pfs[i]:
                        new_stuff = True
                        break

            # If the param files are identical, we continue in loading process
            if not new_stuff:
                break

            # Variables updated
            gd = update_global(new_pfs, self.__defs, self.__gui_defaults, silent=False)
            old_pfs = copy.copy(new_pfs)

        # Processing (with includes) for complete file loading
        test_dict = self._load_test_dict(self.__fname, gd)
        return test_dict, new_pfs


    def run(self):
        try:
            try:
                # Thread for stdout redirection
                in_stream = StringQueue()
                self.redir = Thread(target=self.send_stdout, args=[in_stream])
                self.redir.daemon = True
                stdio_redir.redirect(in_stream)
                self.redir.start()
                test_dir = os.path.dirname(os.path.abspath(self.__fname))

                env_init()

                # Creation of the python evaluation process for loading of the complete test
                eval_proc = eval_process_init("", api_request, 10, test_dir)
                eval_proc.start()
                tm.print_debug(f"python bin is: '{eval_proc.python_bin}'.")
                if not eval_proc.wait_ready(10):
                    raise ETUMRuntimeError(
                                        f"""Impossible to start the external python execution process.
Is the python exec path correct ?"""
                    )

                try:

                    # Loading of the param files without inclusions (first level)
                    init_param_files, glob_variables = self._load_initial_params(test_dir)

                    # Load the test file
                    test_dict, param_files = self._load_test(init_param_files, glob_variables)

                    # Backup the global dict in case of restart of the test
                    gdict = backup_gd()

                    # Now create the test structure and objects
                    test_set = TestSet(self.__fname, test_dict, self.__squeue)

                    # Thread for incoming control commands
                    self.init_commands(test_set)
                    self.cmd_th = Thread(
                        target=self.process_control_commands,
                        args=[self.__tctrl],
                        daemon=True,
                    )
                    self.cmd_th.start()

                    # Set the report path
                    test_set.report_path = locate_report_file(test_set.report_path)
                    self.__loaded = True

                    while True:
                        # waiting for a control command
                        while (not self.__exec) and (not self.__closed):
                            sleep(0.2)
                        # if close is required
                        if self.__closed:
                            break
                        # Test is started
                        try:
                            try:
                                try:
                                    test_run_init()
                                    print(test_run_header())
                                    globdict.set_update_queue(self.__squeue)
                                    test_set.execute()
                                finally:
                                    if test_set.success():
                                        print("Test run success.")
                                    else:
                                        print("Test run failed.")

                                test_set.run_post_exec()
                            finally:
                                self.__exec = False
                                # Stop shared context engines before restore_gd wipes them
                                for engine in tm.gd("_py_func_contexts", {}).values():
                                    engine.stop()
                                    engine.join()
                                for engine in tm.gd("_lua_func_contexts", {}).values():
                                    engine.stop()
                                    engine.join()
                                # Sends signal to the GUI
                                self.send_finished()
                                globdict.set_update_queue(None)
                                restore_gd(gdict)
                        except Exception as e:
                            print_exception(e)

                finally:
                    # Stop python eval execution process
                    eval_proc.stop()
                    eval_proc.join()
                    # Stop shared func context engines (keep_context_id)
                    for engine in tm.gd("_py_func_contexts", {}).values():
                        engine.stop()
                        engine.join()
                    for engine in tm.gd("_lua_func_contexts", {}).values():
                        engine.stop()
                        engine.join()

            except Exception as e:
                print_exception(e)

        finally:
            self.exit()

    def init_commands(self, test_set: TestSet):
        self.__cmds = {
            "pause": test_set.pause,
            "cont": test_set.cont,
            "tree": test_set.tree,
            "report": test_set.set_report,
            "stop": test_set.stop,
            "loaded": self.loaded,
            "execute": self.execute,
            "add_breakpoint": test_set.addBreakpoint,
            "del_breakpoint": test_set.delBreakpoint,
            "skipped_state": test_set.getSkippedState,
            "enabled_state": test_set.getEnabledState,
            "process_param": self.process_param,
            "set_test_outputs": self.set_test_outputs,
            "get_gd_vars": self.get_gd_vars,
            "set_gd_var": self.set_gd_var,
            "del_gd_var": self.del_gd_var,
            "set_enabled_state": test_set.setEnabledState,
            "check_uncheck_all": test_set.checkUncheckAll,
            "get_folded": test_set.getFolded,
            "close": self.close,
        }

    def exit(self):
        self.__closed = True
        if hasattr(self, "cmd_th"):
            self.cmd_th.join()
        self.redir.join()
        stdio_redir.restore()
        stdio_redir.stop()

    def send_finished(self):
        status = {"id": None, "name": "test_process", "status": "finished"}
        self.__squeue.put(status)

    def execute(self):
        self.__exec = True

    def loaded(self):
        return self.__loaded

    def close(self):
        self.__closed = True

    def process_param(self, param):
        return expanse(param)

    def set_test_outputs(self, outputs: list):
        tm.setgd("test_outputs", outputs)

    def get_gd_vars(self):
        import json
        result = {}
        for k, v in globdict.global_dict.items():
            if k.startswith("_"):
                continue
            try:
                json.dumps(v)
                result[k] = v
            except (TypeError, ValueError):
                pass
        return result

    def set_gd_var(self, name: str, value):
        tm.setgd(name, value)

    def del_gd_var(self, name: str):
        tm.delgd(name)

    def process_control_commands(self, tctrl):
        term = False
        while (not term) and (not self.__closed):
            cmd = ""
            res = None
            args = {}
            try:
                qcontent = tctrl.ctrl.get(timeout=0.2)
                try:
                    cmd = list(qcontent.keys())[0]
                    args = qcontent[cmd]
                    if cmd == "exit":
                        term = True
                        break
                    try:
                        if isinstance(args, dict):
                            res = {cmd: self.__cmds[cmd](**args)}
                        elif args is None:
                            res = {cmd: self.__cmds[cmd]()}
                        else:
                            raise ETUMRuntimeError("Test process control command malformed")
                    except ETUMRuntimeError as e:
                        res = (None, str(e))
                    except:
                        res = (None, "function unknown or call failed")
                except:
                    res = (None, "Malformed command")
                tctrl.resp.put(res)
            except Empty:
                continue

    def redirect_stdout(self):
        pconn, cconn = Pipe()
        redir = Thread(target=self.capture_stdout, args=(cconn,))
        redir.daemon = True
        redir.start()
        return pconn

    def send_stdout(self, stream):
        while not self.__closed:
            try:
                data = stream.read(block=True, timeout=0.2)
                if data != "":
                    self.__pconn.send(data)
            except RuntimeError:
                continue

    def capture_stdout(self, cconn):
        while True:
            try:
                # read the pipe data
                data = cconn.recv()
                print(data, end="")
            except EOFError:
                # exit the loop is the pipe is closed
                break
