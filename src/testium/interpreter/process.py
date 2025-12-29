import os
import sys
from multiprocessing import Process, Queue, Pipe
from queue import Empty
from threading import Thread
from time import sleep
import traceback

import libs.testium as tm
from interpreter.utils.params import expanse
from interpreter.utils.string_queue import StringQueue
from interpreter.utils.test_ctrl import TestSetController
from interpreter.utils.test_init import (
    env_init,
    load_test,
    test_run_init,
    test_run_header,
    locate_report_file,
    backup_gd,
    restore_gd,
)
from interpreter.test_set import TestSet
from interpreter.utils.stdout_redirect import stdio_redir
from interpreter.utils.tum_except import print_exception
from interpreter.utils.func_exec import func_call_init
from interpreter.utils.api_srv import api_request


class TestProcess(Process):
    def __init__(
        self,
        file_name,
        status_queue: Queue,
        tst_control: TestSetController,
        config_files,
        defines,
    ) -> None:
        super().__init__()
        self.__fname = file_name
        self.__squeue = status_queue
        self.__tctrl = tst_control
        self.__cfgf = config_files
        self.__defs = defines
        self.__exec = False
        self.__loaded = False
        self.__closed = False
        self.__pconn = self.redirect_stdout()

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

                # Load the test file
                test_dict, cfg_files = load_test(
                    self.__fname, test_dir, self.__cfgf, self.__defs)

                # Backup the global dict in case of restart of the test
                gdict = backup_gd()

                # The path of the test file is included in PYTHONPATH
                sys.path.append(os.path.dirname(self.__fname))

                # Now create the test structure and objects
                test_set = TestSet(self.__fname, test_dict, self.__squeue)

                # Thread for incoming control commands
                self.init_commands(test_set)
                self.cmd_th = Thread(
                    target=self.process_control_commands, args=[self.__tctrl])
                self.cmd_th.daemon = True
                self.cmd_th.start()

                test_set.report_path = locate_report_file(test_set.report_path)

                # Python functions call subprocess initialization
                fproc = func_call_init(tm.gd("python_path", ""), api_request)

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
                                fproc.start()
                                fproc.wait_ready()
                                test_set.execute()
                            finally:
                                if test_set.success():
                                    print("Test run success.")
                                else:
                                    print("Test run failed.")

                            test_set.run_post_exec()
                        finally:
                            # Stop function execution process
                            fproc.stop()
                            fproc.join()
                            self.__exec = False
                            # Sends signal to the GUI
                            self.send_finished()
                            restore_gd(gdict)
                    except Exception as e:
                        print_exception(e)

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
        status = {'id': None,
                  'name': "test_process",
                  'status': 'finished'}
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
                    except:
                        res = (None, "function unknown or call failed")
                except:
                    res = (None, "Malformed command")
                tctrl.resp.put(res)
            except Empty:
                continue

    def redirect_stdout(self):
        pipe = pconn, cconn = Pipe()
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
