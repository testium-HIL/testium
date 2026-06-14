"""``pytest`` test item.

Runs a user pytest file and surfaces every collected test as a child item
(one PASS / FAIL / SKIP per test, with duration and failure message in the
report) — the pytest analogue of the ``unittest`` item.

Unlike ``unittest`` (which runs in-process), pytest runs in a **subprocess on
the host interpreter** (``bins.python_bin()``), exactly like ``py_func`` /
``lua_func``. This keeps the user's pytest install and test dependencies on
the host (visible across every packaging channel — source, wheel, PyInstaller,
Flatpak, AppImage) instead of requiring them inside the bundled interpreter.

A tiny stdlib-only pytest plugin (written to a temp dir and loaded with
``-p``) streams the collected node ids and per-test results back over the
subprocess stdout as sentinel-prefixed lines, which the parent parses live.
"""

import os
import json
import shutil
import atexit
import tempfile
import threading
import queue
import subprocess

import api.testium as tm
from runtime.tum_except import ETUMFileError, ETUMRuntimeError
from interpreter.test_items.test_item import TestItem, test_run, test_data
from interpreter.test_items.test_result import TestResult, TestValue
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.param_decl import Param, ParamSet, LIST
from interpreter.utils.paths import no_window_kwargs
from interpreter.utils import bins


# Sentinels streamed by the in-subprocess plugin (see _PLUGIN_SOURCE). Kept in
# sync with the plugin source below.
_SENT_COLLECTED = "__TESTIUM_PYTEST_COLLECTED__"
_SENT_START = "__TESTIUM_PYTEST_START__"
_SENT_RESULT = "__TESTIUM_PYTEST_RESULT__"

_PLUGIN_MODULE = "_testium_pytest_plugin"

# stdlib-only pytest plugin executed inside the host subprocess. It must not
# import anything from testium. It emits one sentinel line per event so the
# parent can rebuild the test tree (collection) and per-test results (run)
# without parsing pytest's human output or a JUnit XML.
_PLUGIN_SOURCE = '''\
import sys
import json

_SENT_COLLECTED = "__TESTIUM_PYTEST_COLLECTED__"
_SENT_START = "__TESTIUM_PYTEST_START__"
_SENT_RESULT = "__TESTIUM_PYTEST_RESULT__"

_reports = {}


def _emit(payload):
    # Leading newline guarantees the sentinel starts its own line even if a
    # test printed without a trailing newline (pytest runs with --capture=no).
    sys.stdout.write("\\n" + payload + "\\n")
    sys.stdout.flush()


def pytest_collection_modifyitems(session, config, items):
    _emit(_SENT_COLLECTED + json.dumps([it.nodeid for it in items]))


def pytest_runtest_logstart(nodeid, location):
    _emit(_SENT_START + nodeid)


def pytest_runtest_logreport(report):
    _reports.setdefault(report.nodeid, {})[report.when] = report


def _skip_reason(report):
    lr = report.longrepr
    if isinstance(lr, tuple) and len(lr) == 3:
        return str(lr[2])
    return report.longreprtext or ""


def pytest_runtest_logfinish(nodeid, location):
    phases = _reports.pop(nodeid, {})
    setup = phases.get("setup")
    call = phases.get("call")
    teardown = phases.get("teardown")

    duration = 0.0
    for rep in (setup, call, teardown):
        if rep is not None:
            duration += getattr(rep, "duration", 0.0) or 0.0

    outcome = "pass"
    message = ""
    if setup is not None and setup.failed:
        outcome, message = "fail", setup.longreprtext
    elif setup is not None and setup.skipped:
        outcome, message = "skip", _skip_reason(setup)
    elif call is not None:
        if call.failed:
            outcome, message = "fail", call.longreprtext
        elif call.skipped:
            outcome, message = "skip", _skip_reason(call)
        else:
            outcome = "pass"
    if teardown is not None and teardown.failed and outcome == "pass":
        outcome, message = "fail", teardown.longreprtext

    _emit(_SENT_RESULT + json.dumps({
        "nodeid": nodeid,
        "outcome": outcome,
        "message": message,
        "duration": duration,
    }))
'''


class TestItemPytestElement(TestItem):
    """One collected pytest test (leaf child of a pytest file item)."""

    def __init__(self, name, parent=None, status_queue=None, filename=""):
        super().__init__(None, parent, status_queue, filename=filename)
        self.is_container = False
        self._name = name
        self._type = cst.TYPE_PYTEST_STEP
        self.banner = ""
        self.footer = ""
        self._nodeid = ""
        self._reported_done = False


class TestItemPytestFile(TestItem):

    PARAMS = ParamSet(
        Param("test_file", required=True,
              doc="Path to the pytest test file."),
        Param("test_method", kind=LIST,
              doc="Optional list of test function names to restrict the run "
                  "to (matched against the function part of each node id, "
                  "parametrisation suffix stripped). When empty, every "
                  "collected test in the file is run."),
    )

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        self._name = cst.TYPE_PYTEST.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self.is_container = True
        self._type = cst.TYPE_PYTEST
        self._fileName = self._prms.getParam('test_file', required=True, processed=True)
        self._testDir = ''
        self._test_methods = self._prms.getParamAll('test_method', processed=True)
        self._cwd = ""
        self._plugin_dir = ""

    def setTestDir(self, dir):
        self._testDir = dir

    # ---- subprocess plumbing -------------------------------------------------

    def _write_plugin(self):
        # In Flatpak the host process can only read /tmp (shared), so stage the
        # plugin there; outside Flatpak the default temp dir is fine.
        d = tempfile.mkdtemp(prefix="testium_pytest_",
                             dir="/tmp" if bins._in_flatpak() else None)
        with open(os.path.join(d, _PLUGIN_MODULE + ".py"), "w") as f:
            f.write(_PLUGIN_SOURCE)
        atexit.register(shutil.rmtree, d, ignore_errors=True)
        return d

    def _pytest_popen(self, args):
        pbin = bins.python_bin()
        if not pbin:
            raise ETUMRuntimeError("No valid Python 3 interpreter found")

        env = os.environ.copy()
        bins.apply_host_libs(env)
        env.pop("PYTHONUSERBASE", None)
        env["PYTHONPATH"] = self._plugin_dir + os.pathsep + env.get("PYTHONPATH", "")

        cmd_args = [
            "-m", "pytest",
            "--capture=no",      # let plugin sentinels + test prints reach our pipe
            "-o", "addopts=",    # neutralise user addopts (xdist/cov break parsing)
            "-p", "no:cacheprovider",
            "-p", _PLUGIN_MODULE,
            *args,
        ]

        if bins._in_flatpak():
            host_env = {k: env[k] for k in ("PYTHONPATH", "PATH") if env.get(k)}
            params = bins.flatpak_host_spawn(
                pbin, cmd_args, host_cwd=self._cwd, extra_env=host_env)
            popen_kwargs = {}
        else:
            params = [pbin, *cmd_args]
            popen_kwargs = {"env": env, "cwd": self._cwd}

        return subprocess.Popen(
            params,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            restore_signals=False,
            **no_window_kwargs(),
            **popen_kwargs,
        )

    # ---- loading (collection) ------------------------------------------------

    def _collect(self):
        proc = self._pytest_popen(["--collect-only", "-q", self._fileName])
        nodeids = []
        output = []
        for line in proc.stdout:
            line = line.rstrip("\n")
            if line.startswith(_SENT_COLLECTED):
                try:
                    nodeids = json.loads(line[len(_SENT_COLLECTED):])
                except ValueError:
                    pass
            elif line != "":
                output.append(line)
        proc.wait()
        return nodeids, "\n".join(output)

    def _collection_error(self, output):
        """Clear reason why collection produced no test."""
        if "No module named pytest" in output:
            return ("pytest is not installed on the host interpreter used by "
                    "testium (python_bin). Install it, e.g. 'pip install pytest'.")
        return 'No pytest test collected from "%s".\n%s' % (self._fileName, output)

    def load(self):
        ret = {}
        if self._fileName == '':
            raise ETUMFileError('A file name is expected but got "None"')

        if not os.path.isabs(self._fileName):
            self._fileName = os.path.normpath(os.path.join(self._testDir, self._fileName))
        if not os.path.isfile(self._fileName):
            raise ETUMFileError('File "%s" is not found' % (self._fileName))

        self._cwd = os.path.dirname(self._fileName) or "."
        self._plugin_dir = self._write_plugin()

        nodeids, output = self._collect()
        if not nodeids:
            raise ETUMFileError(self._collection_error(output))

        if self._test_methods:
            present = {nid.split("::")[-1].split("[")[0] for nid in nodeids}
            for m in self._test_methods:
                if m not in present:
                    raise ETUMFileError(
                        'Test function "%s" is not found in "%s"' % (m, self._fileName))
            wanted = set(self._test_methods)
            nodeids = [nid for nid in nodeids
                       if nid.split("::")[-1].split("[")[0] in wanted]

        for nid in nodeids:
            disp = nid.split("::", 1)[1] if "::" in nid else nid
            item = TestItemPytestElement(disp, self)
            item._nodeid = nid
            ret.update(test_data(item, {}))

        return ret

    # ---- execution (run) -----------------------------------------------------

    def _finish_child(self, child, value, message=""):
        if child._reported_done:
            return
        if getattr(child, "t0", None) is None:
            child.t0 = tm.timestamp()
            self.status_queue.put(
                {'id': child.id(), 'status': 'started', 'timestamp': child.t0})
        child.duration = tm.timestamp() - child.t0
        res = TestResult(child, value, message)
        res.test_id = child.id()
        res.sendStatus(self.status_queue)
        self.status_queue.put(
            {'id': child.id(), 'status': 'finished', 'duration': child.duration})
        self.report.addTest(child, res)
        child._reported_done = True

    def _stream_results(self, proc, by_nodeid):
        overall = TestValue.SUCCESS
        outq = queue.Queue()

        def reader():
            for line in proc.stdout:
                outq.put(line)
            outq.put(None)

        t = threading.Thread(target=reader, daemon=True)
        t.start()

        while True:
            try:
                line = outq.get(timeout=0.1)
            except queue.Empty:
                if self.isStopped():
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    break
                continue
            if line is None:
                break
            line = line.rstrip("\n")

            if line.startswith(_SENT_COLLECTED):
                # pytest re-collects at the start of the run; the node list was
                # already consumed at load time, so drop it here.
                continue
            elif line.startswith(_SENT_START):
                child = by_nodeid.get(line[len(_SENT_START):])
                if child is not None and getattr(child, "t0", None) is None:
                    child.t0 = tm.timestamp()
                    self.status_queue.put(
                        {'id': child.id(), 'status': 'started', 'timestamp': child.t0})
            elif line.startswith(_SENT_RESULT):
                try:
                    rec = json.loads(line[len(_SENT_RESULT):])
                except ValueError:
                    continue
                child = by_nodeid.get(rec.get("nodeid"))
                if child is None:
                    continue
                value = {
                    "pass": TestValue.SUCCESS,
                    "fail": TestValue.FAILURE,
                    "skip": TestValue.NORUN,
                }.get(rec.get("outcome"), TestValue.FAILURE)
                self._finish_child(child, value, rec.get("message", ""))
                if value == TestValue.FAILURE:
                    overall = TestValue.FAILURE
            elif line != "":
                print(line)

        proc.wait()
        return overall

    @test_run
    def execute(self):
        by_nodeid = {}
        enabled_nodeids = []
        for i in range(self.childCount()):
            c = self.child(i)
            c.t0 = None
            c._reported_done = False
            by_nodeid[c._nodeid] = c
            if c.enabled:
                enabled_nodeids.append(c._nodeid)
            else:
                self._finish_child(c, TestValue.NORUN, "test disabled")

        overall = TestValue.SUCCESS
        if enabled_nodeids and not self.isStopped():
            args = list(enabled_nodeids)
            if self._stop_on_failure:
                args.append("-x")
            proc = self._pytest_popen(args)
            overall = self._stream_results(proc, by_nodeid)

        # Any enabled test that produced no result (crash, -x stop, user stop)
        # is reported as NORUN so the tree stays consistent.
        for i in range(self.childCount()):
            c = self.child(i)
            if c.enabled and not c._reported_done:
                self._finish_child(c, TestValue.NORUN, "not executed")

        if self.isStopped():
            self.result.set(TestValue.NORUN, 'pytest execution aborted on user request')
        else:
            self.result.set(overall, 'pytest ' + str(overall))
