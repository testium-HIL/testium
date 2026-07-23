import json
import os
import shlex
import subprocess
import tempfile
import threading
from functools import wraps
import sqlite3
from time import (time, sleep)
import traceback
from runtime.tum_except import (ETUMRuntimeError, ETUMSyntaxError)
from runtime.stdout_redirect import stdio_redir
from interpreter.utils.params import (expanse)
from interpreter.utils.paths import prepare_file_to_save, no_window_kwargs
from interpreter.utils import bins
import api.testium as tm
import interpreter.utils.constants as cst
from interpreter.utils.constants import TestItemType as cst_type
from interpreter.test_report.report_interface import (adapt_json, convert_json)

sqlite3.register_adapter(dict, adapt_json)
sqlite3.register_adapter(list, adapt_json)
sqlite3.register_adapter(tuple, adapt_json)
sqlite3.register_converter('JSON', convert_json)

TEST_REPORT_FILE_REV = '0.1'


def _load_text():
    from interpreter.test_report.report_export_txt import ReportExportTxt
    return ReportExportTxt

def _load_json():
    from interpreter.test_report.report_export_json import ReportExportJSON
    return ReportExportJSON

def _load_junit():
    try:
        from interpreter.test_report.report_export_junit import ReportExportJUnit
        return ReportExportJUnit
    except ModuleNotFoundError:
        raise ETUMRuntimeError(
            'Report format "junit" requires "junit_xml" — pip install junit-xml')

def _load_html():
    try:
        from interpreter.test_report.report_export_html import ReportExportHTML
        return ReportExportHTML
    except ModuleNotFoundError:
        raise ETUMRuntimeError(
            'Report format "html" requires "lxml" — pip install lxml')

_EXPORTER_REGISTRY: dict = {
    cst.REP_TYPE_TEXT:  _load_text,
    cst.REP_TYPE_JSON:  _load_json,
    cst.REP_TYPE_JUNIT: _load_junit,
    cst.REP_TYPE_HTML:  _load_html,
}

# Third-party exporter plugins (entry-point group "testium.exporters") are
# NOT loaded in this process: the bundled interpreter of the Flatpak /
# AppImage / PyInstaller channels is read-only, so the user could never pip
# install into it. Non-builtin formats are handed to runtime/export_worker.py
# running on the host Python (bins.python_bin()), same philosophy as py_func.

# Must match export_worker.py.
_WORKER_FORMATS_SENTINEL = "__TESTIUM_EXPORT_FORMATS__="
_WORKER_EXIT_UNKNOWN_FORMAT = 3


def _db_snapshot(con):
    """Copy the report database to a temp SQLite file and return its path.

    Out-of-process exporters can't use the live connection (which may be
    ``:memory:`` when no ``sqlite`` export is configured), and in Flatpak the
    host only sees shared paths — /tmp is shared via the manifest.
    """
    tmp_dir = "/tmp" if os.path.isdir("/tmp") else None
    fd, tmp = tempfile.mkstemp(prefix="testium_report_", suffix=".sqlite",
                               dir=tmp_dir)
    os.close(fd)
    # Mid-run the connection holds an open write transaction (addTest INSERTs
    # are committed at close); backup() from the same connection then retries
    # on SQLITE_BUSY forever. Commit first — nothing relies on rollback.
    try:
        con.commit()
    except sqlite3.Error:
        pass
    dst = sqlite3.connect(tmp)
    try:
        con.backup(dst)
    finally:
        dst.close()
    return tmp


def _run_on_host(argv, cwd=None):
    """Run *argv* on the host: flatpak-spawn --host in Flatpak, plain
    subprocess elsewhere (with the AppImage bundle-local env scrubbed).
    Returns a CompletedProcess, or None if the spawn itself failed."""
    if cwd is None or not os.path.isdir(cwd):
        cwd = "/tmp" if os.path.isdir("/tmp") else None
    if bins._in_flatpak():
        argv = bins.flatpak_host_spawn(argv[0], argv[1:], host_cwd=cwd)
        kwargs = {}
    else:
        env = os.environ.copy()
        bins.apply_host_libs(env)
        env.pop("PYTHONUSERBASE", None)
        kwargs = {"env": env, "cwd": cwd}
    try:
        return subprocess.run(argv, capture_output=True, text=True,
                              **no_window_kwargs(), **kwargs)
    except (FileNotFoundError, PermissionError, OSError):
        return None


def tr_procedure(f):
    @wraps(f)
    def wrapper(self, *args, **kwds):
        if not self._active:
            return
        return f(self, *args, **kwds)
    return wrapper


class Export:

    def __init__(self, dict_export, con=None):
        if (not isinstance(dict_export, dict)) or (len(dict_export) != 1):
            raise ETUMSyntaxError(
                    'Syntax error in the report export description')

        self.con = con
        self.type = list(dict_export.keys())[0]
        self.tum_pattern = dict_export[self.type].get('pattern', [])
        self.tum_key = dict_export[self.type].get('key', [])
        self.path = dict_export[self.type].get('path', '')
        self.filename = dict_export[self.type].get('file_name', '')
        self.tum_cmd = dict_export[self.type].get('cmd', '')

        if len(self.tum_pattern) > 0:
            if not isinstance(self.tum_pattern, (list, str)):
                raise ETUMSyntaxError(
                    'pattern must be a string or a list of string')
            if isinstance(self.tum_pattern, (str)):
                self.tum_pattern = [self.tum_pattern]

        if len(self.tum_key) > 0:
            if not isinstance(self.tum_key, (list, str)):
                raise ETUMSyntaxError(
                    'pattern must be a string or a list of string')
            if isinstance(self.tum_key, (str)):
                self.tum_key = [self.tum_key]

    def exec(self, con=None, name : str ='', no_header: bool = False):
        if con is None:
            con = self.con

        if con is None:
            return

        pats = []
        for p in self.tum_pattern:
            pats.append(expanse(p))

        keys = []
        for k in self.tum_key:
            keys.append(expanse(k))

        et = expanse(self.type)
        path = expanse(self.path)
        fname = expanse(self.filename)
        if fname != '' and path == '':
            path = fname
        elif fname == '' and path != '':
            pass
        else:
            path = os.path.join(path, fname)

        if et == cst.REP_TYPE_SQLITE:
            pass
        elif et == cst.REP_TYPE_COMMAND:
            self._exec_command(con, path)
        elif et in _EXPORTER_REGISTRY:
            try:
                cls = _EXPORTER_REGISTRY[et]()
                cls(name, con, path, pats, keys, no_header)
            except ETUMRuntimeError as e:
                print(f'[report] Export skipped: {e}')
        else:
            self._exec_plugin(con, et, name, path, pats, keys, no_header)

    @staticmethod
    def _available(plugins=()):
        return ', '.join(sorted(
            list(_EXPORTER_REGISTRY.keys())
            + [cst.REP_TYPE_SQLITE, cst.REP_TYPE_COMMAND]
            + list(plugins)))

    def _exec_plugin(self, con, et, name, path, pats, keys, no_header):
        """Run a non-builtin export format through the host-side worker
        (entry-point plugins are installed on the host Python)."""
        pbin = bins.python_bin()
        if not pbin:
            print(f'[report] Export skipped: format "{et}" needs a host '
                  'Python 3 interpreter and none was found.')
            return
        worker = os.path.join(bins._get_host_testium_path(),
                              'runtime', 'export_worker.py')
        db = _db_snapshot(con)
        payload = json.dumps({'format': et, 'db': db, 'path': path,
                              'pats': pats, 'keys': keys,
                              'no_header': no_header, 'name': name})
        try:
            r = _run_on_host([pbin, worker, payload])
        finally:
            try:
                os.unlink(db)
            except OSError:
                pass

        if r is None:
            print(f'[report] Export skipped: format "{et}": could not start '
                  f'the host Python "{pbin}".')
            return
        if r.returncode == _WORKER_EXIT_UNKNOWN_FORMAT:
            plugins = []
            for line in r.stdout.splitlines():
                if line.startswith(_WORKER_FORMATS_SENTINEL):
                    names = line[len(_WORKER_FORMATS_SENTINEL):]
                    plugins = [n for n in names.split(',') if n]
            print(f'[report] Export skipped: format "{et}" not found. '
                  f'Available: {self._available(plugins)}')
            return
        if r.stdout.strip():
            print(r.stdout.rstrip())
        if r.returncode != 0:
            detail = r.stderr.strip() or f'exit code {r.returncode}'
            print(f'[report] Export skipped: {detail}')

    def _exec_command(self, con, path):
        """Run an external tool on the host with a temp copy of the report
        database. Placeholders in cmd: {db} (SQLite copy), {out} (path)."""
        cmd = expanse(self.tum_cmd)
        if not isinstance(cmd, str) or not cmd.strip():
            print('[report] Export skipped: the "command" export needs a '
                  'non-empty "cmd" string.')
            return
        db = _db_snapshot(con)
        try:
            try:
                argv = [tok.format(db=db, out=path)
                        for tok in shlex.split(cmd)]
            except (KeyError, IndexError, ValueError) as e:
                print(f'[report] Export skipped: bad placeholder in command '
                      f'"{cmd}" ({e}). Supported: {{db}}, {{out}}.')
                return
            # Test directory as cwd so relative paths in cmd behave as in
            # the rest of the .tum.
            r = _run_on_host(argv, cwd=tm.gd('test_directory', None))
            if r is None:
                print(f'[report] Export skipped: could not start command '
                      f'"{argv[0]}".')
                return
            if r.stdout.strip():
                print(r.stdout.rstrip())
            if r.returncode != 0:
                detail = r.stderr.strip()
                print(f'[report] Export skipped: command "{argv[0]}" exited '
                      f'with code {r.returncode}'
                      + (f': {detail}' if detail else '.'))
        finally:
            try:
                os.unlink(db)
            except OSError:
                pass

class TestReport:
    TEST_COLS = [[cst.DB_TEST_TIMESTAMP_START, 'INT'],
                 [cst.DB_TEST_ID, 'INT NOT NULL'],
                 [cst.DB_TEST_PARENT_ID, 'INT'],
                 [cst.DB_TEST_LEVEL, 'INT'],
                 [cst.DB_TEST_NAME, 'TEXT'],
                 [cst.DB_TEST_TYPE, 'TEXT'],
                 [cst.DB_TEST_KEY, 'TEXT'],
                 [cst.DB_TEST_RESULT, 'TEXT'],
                 [cst.DB_TEST_MESSAGE, 'TEXT'],
                 [cst.DB_TEST_DURATION, 'INT'],
                 [cst.DB_TEST_LOG, 'TEXT'],
                 [cst.DB_TEST_DATA, 'JSON'],
                 ]

    @classmethod
    def indexOf(cls, name):
        i = 0
        for l in cls.TEST_COLS:
            if l[0] == name:
                break
            i = i + 1
        return i

    @classmethod
    def export_to_dict(cls, etype, filename, path, pattern, key):
        return {etype: {'file_name': filename, 'path': path,
                        'pattern': pattern, 'key': key}}

    def __init__(self, dict_report):
        self._path = ""
        self.tum_path = ''
        self.has_sqlite = False
        self._active = True
        self.export = []
        self.tum_export = []
        self._level = 0
        self._log_stored = False
        self._con = None
        self._lock = threading.Lock()

        if dict_report is None:
            self._active = False
            return

        # Process parameters
        a = expanse(dict_report.get('enabled', True))
        if isinstance(a, bool):
            self._active = a
        else:
            if str(a).lower() == 'false':
                self._active = False

        if self._active:
            self.dict_report = dict_report
            ls = expanse(dict_report.get('log_stored', False))
            if isinstance(ls, bool):
                self._log_stored = ls
            else:
                if str(ls).lower() == 'true':
                    self._log_stored = True

            exports = self.dict_report.get('export', [])
            if isinstance(exports, dict):
                exports = [{k: v} for k, v in exports.items()]
            for exp in exports:
                self.add_export(self.tum_export, exp)

        if self._log_stored:
            stdio_redir.intercept()

    # Path
    @property
    def path(self):
        ret = self.tum_path
        if self._path != '':
            ret = self._path
        return ret

    @path.setter
    def path(self, value):
        self._path = value
        if (self._path != '') and (self._active == False):
            self._log_stored = True
            self._active = True
            stdio_redir.intercept()

        for exp in self.exports:
            exp.path = self.path

    # export
    @property
    def exports(self):
        ret = self.tum_export
        if len(self.export) > 0:
            ret = self.export
        return ret

    @exports.setter
    def exports(self, exp):
        self.add_export(self.export, exp)
        if (len(self.export) > 0):
            self._active = True

    def add_export(self, elist, exp):
        e = Export(exp)
        elist.append(e)
        if e.type == cst.REP_TYPE_SQLITE:
            self.has_sqlite = True
            self.tum_path = e.path
            if e.filename != '':
                self.tum_path = os.path.join(self.tum_path, e.filename)

    @property
    def db_connection(self):
        return self._con

    @tr_procedure
    def open(self, header):

        rep_path = self.path
        if not self.has_sqlite:
            rep_path = ':memory:'
        else:
            rep_path = expanse(rep_path)
            prepare_file_to_save(rep_path)
            if not os.path.exists(os.path.dirname(rep_path)):
                raise ETUMRuntimeError("Report path does not exist: " + rep_path)
        self._con = sqlite3.connect(rep_path, check_same_thread=False)
        self.createHeader(header)
        self.createTestTable()
        self._con.commit()

    @tr_procedure
    def close(self, header):
        try:
            try:
                for k, v in header.items():
                    self._con.execute(
                        "INSERT INTO header VALUES('{}', '{}')".format(k, v))
                self._con.commit()

                # stop stdout interception thread
                stdio_redir.stop()

                for export in self.exports:
                    export.exec(self._con)

            except:
                print(traceback.format_exc())
        finally:
            self._con.close()

    @tr_procedure
    def createHeader(self, header):
        self._con.execute("CREATE TABLE header(key TEXT, value TEXT)")
        self._con.execute("INSERT INTO header VALUES(?, ?)", (cst.DB_REPORT_VERSION,
                                                              TEST_REPORT_FILE_REV))
        for k, v in header.items():
            self._con.execute(
                "INSERT INTO header VALUES('{}', '{}')".format(k, v))

    @tr_procedure
    def createTestTable(self):
        req = ''
        for l in self.TEST_COLS:
            req = req + l[0] + ' ' + l[1] + ','
        req = req[:-1]
        self._con.execute('CREATE TABLE tests(' + req + ')')

    @tr_procedure
    def addTest(self, test_item, result, key=None):
        p = test_item.parent()
        pid = None
        if p is not None:
            pid = p.id()
        param = ()
        for l in self.TEST_COLS:
            if l[0] == cst.DB_TEST_TIMESTAMP_START:
                param = param + (test_item.t0,)
            elif l[0] == cst.DB_TEST_ID:
                param = param + (test_item.id(),)
            elif l[0] == cst.DB_TEST_PARENT_ID:
                param = param + (pid,)
            elif l[0] == cst.DB_TEST_NAME:
                param = param + (test_item.name(),)
            elif l[0] == cst.DB_TEST_TYPE:
                param = param + (test_item.type(),)
            elif l[0] == cst.DB_TEST_KEY:
                skey = key
                if isinstance(key, list):
                    skey = ""
                    for k in key:
                        skey += f"{k}, "
                    skey = skey if len(key) == 0 else skey[:-len(", ")]
                param = param + (skey,)
            elif l[0] == cst.DB_TEST_RESULT:
                param = param + (str(result.test_result),)
            elif l[0] == cst.DB_TEST_MESSAGE:
                param = param + (str(result.message),)
            elif l[0] == cst.DB_TEST_DURATION:
                param = param + (test_item.duration,)
            elif l[0] == cst.DB_TEST_DATA:
                param = param + (result.reported,)
            elif l[0] == cst.DB_TEST_LEVEL:
                param = param + (self._level,)
            elif l[0] == cst.DB_TEST_LOG:
                if self._log_stored and (test_item.type() != cst_type.TYPE_ROOT.item_name):
                    lo = ''
                    pat = test_item.footer
                    t0 = time()
                    while pat != "":
                        lo = lo + stdio_redir.read()
                        if (pat in lo):
                            break
                        if (time() - t0) < 10.0:
                            sleep(0.1)
                        else:
                            break

                    param = param + (lo,)
                else:
                    param = param + ('',)
            else:
                raise ETUMRuntimeError('unknow database key')

        req = 'INSERT INTO tests VALUES('
        for l in self.TEST_COLS:
            req = req + '?,'
        req = req[:-1] + ')'

        with self._lock:
            self._con.execute(req, param)

    def incLevel(self):
        self._level = self._level + 1

    def decLevel(self):
        if self._level > 0:
            self._level = self._level - 1
