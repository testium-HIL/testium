import os
import configparser
import json
import platform
from runtime.tum_except import ETUMRuntimeError

SettingsCompany = 'Testium'
SettingsApplication = 'testium'


def host_id():
    """Short host name usable in a file name ('localhost' if unknown)."""
    node = platform.node().split('.')[0]
    node = ''.join(c for c in node if c.isalnum() or c in '-_')
    return node or 'localhost'


def init():
    global settings
    settings = TestiumSettings()


_UNSET = object()


class SettingsItem():
    def __init__(self, name: str, item_type: type, default=None) -> None:
        self.name = name
        self.t = item_type
        self.default = default


def _pref(item):
    """Build a get/set property reading/writing *item* (default carried by the item)."""
    return property(lambda self: self.value(item),
                    lambda self, value: self.set_value(item, value))


class TestiumSettings():
    SettingsRecentFiles = SettingsItem('recentFileList', list, [])
    SettingsLastLogFile = SettingsItem('lastLogFile', str, '')
    SettingsLogFileSaved = SettingsItem('logFileSaved', bool, False)
    SettingsHideDocPane = SettingsItem('docPaneHidden', bool, False)
    SettingsHideLogPane = SettingsItem('logPaneHidden', bool, False)
    SettingsShowCheckboxes = SettingsItem('checkBoxesShow', bool, False)
    SettingsLogPath = SettingsItem('defaultLogPath', str, '$(test_directory)')
    SettingsReportPath = SettingsItem('defaultReportPath', str, '$(test_directory)')
    SettingsShowTimeColumn = SettingsItem('showTimeColumn', bool, False)
    SettingsColumnsSize = SettingsItem('columnsSize', dict, {})
    SettingsDblClickEnabled = SettingsItem('dblClickEnabled', bool, False)
    SettingsEditorCmd = SettingsItem('editorCmd', str, 'code -g {file}:{line}')
    SettingsIconsTheme = SettingsItem('iconsTheme', int, 0)
    SettingsLogFont = SettingsItem('logFont', str, 'Monospace')
    SettingsLogFontSize = SettingsItem('logFontSize', int, 8)
    SettingsGitSupported = SettingsItem('logGitSupported', bool, True)
    SettingsPythonPath = SettingsItem('pythonPath', str, '')
    SettingsLuaPath = SettingsItem('luaPath', str, '')
    SettingsDebugOutput = SettingsItem('debugOutput', bool, False)

    recent_files = _pref(SettingsRecentFiles)
    log_file = _pref(SettingsLastLogFile)
    log_file_saved = _pref(SettingsLogFileSaved)
    hide_doc_pane = _pref(SettingsHideDocPane)
    hide_log_pane = _pref(SettingsHideLogPane)
    show_checkboxes = _pref(SettingsShowCheckboxes)
    log_path = _pref(SettingsLogPath)
    report_path = _pref(SettingsReportPath)
    show_time_column = _pref(SettingsShowTimeColumn)
    columns_size = _pref(SettingsColumnsSize)
    dbl_click_enabled = _pref(SettingsDblClickEnabled)
    editor_cmd = _pref(SettingsEditorCmd)
    icons_theme = _pref(SettingsIconsTheme)
    log_font = _pref(SettingsLogFont)
    git_supported = _pref(SettingsGitSupported)
    python_bin = _pref(SettingsPythonPath)
    lua_bin = _pref(SettingsLuaPath)
    debug_output = _pref(SettingsDebugOutput)

    def __init__(self):
        if 'windows' in platform.system().lower():
            user_path = os.getenv('APPDATA')
        else:
            user_path = os.path.join(os.getenv('HOME'), '.config')

        settings_dir = os.path.join(user_path, SettingsCompany,
                                    SettingsApplication)
        # One file per machine: with a network home shared by several PCs,
        # each machine keeps its own paths, geometry and recent files.
        self.settings_fname = os.path.join(
            settings_dir, SettingsApplication + '.' + host_id() + '.conf')

        # Create the directory but never the user config root itself.
        if not os.path.isfile(self.settings_fname) and os.path.isdir(user_path):
            os.makedirs(settings_dir, exist_ok=True)
            try:
                with open(self.settings_fname, "x"):
                    pass
            except FileExistsError:
                pass

        # Keys written or removed by this process; sync() merges only these
        # into the file, so concurrent instances keep each other's keys.
        self._dirty = set()
        self._removed = set()
        self._dirty_all = False

        self.conf = configparser.ConfigParser()
        try:
            self.conf.read(self.settings_fname)
        except (configparser.Error, UnicodeDecodeError):
            # Corrupt file: run on defaults, do not touch the file here.
            self.conf = configparser.ConfigParser()
        if 'Default' not in self.conf:
            self.conf['Default'] = {}

    def clear(self):
        self.conf['Default'] = {}
        self._dirty_all = True
        self.sync()

    def value(self, key: SettingsItem, default=_UNSET):
        if not isinstance(key, SettingsItem):
            raise ETUMRuntimeError(
                f'Not a SettingsItem: {key!r}. '
                f'Internal error, please report it.')
        if default is _UNSET:
            default = key.default
        if type(default) != key.t:
            raise ETUMRuntimeError(
                f'Type mismatch for setting "{key.name}": default is '
                f'{type(default).__name__}, expected {key.t.__name__}. '
                f'Erasing "{self.settings_fname}" may solve the issue.')
        ret = default
        try:
            if key.t == int:
                ret = int(self.conf.getint('Default', key.name, fallback=default))
            elif key.t == bool:
                ret = bool(self.conf.getboolean(
                    'Default', key.name, fallback=default))
            elif key.t == str:
                ret = self.conf.get('Default', key.name, fallback=default)
            elif key.t == bytearray:
                # fallback=None: the default may be an (empty) bytearray,
                # which json.loads rejects — and a failed read here used to
                # clear() the whole in-memory config on first run.
                raw = self.conf.get('Default', key.name, fallback=None)
                ret = default if raw is None else bytearray(json.loads(raw))
            else:
                ret = self.conf.get('Default', key.name, fallback=default)
                if isinstance(ret, str):
                    ret = json.loads(ret)
        except:
            self.clear()
        return ret

    def set_value(self, key: SettingsItem, value: any):
        if type(value) != key.t:
            raise ETUMRuntimeError(
                f'Type mismatch for setting "{key.name}": got '
                f'{type(value).__name__}, expected {key.t.__name__}. '
                f'Erasing "{self.settings_fname}" may solve the issue.')
        if key.t == int:
            self.conf.set('Default', key.name, str(int(value)))
        elif key.t == bool:
            self.conf.set('Default', key.name, str(bool(value)))
        elif key.t == str:
            self.conf.set('Default', key.name, str(value))
        elif key.t == bytearray:
            ba = [int(v) for v in value]
            self.conf.set('Default', key.name, json.dumps(ba))
        else:
            self.conf.set('Default', key.name, json.dumps(value))
        self._dirty.add(key.name.lower())
        self._removed.discard(key.name.lower())

    def remove_value(self, name: str):
        name = name.lower()
        self.conf.remove_option('Default', name)
        self._removed.add(name)
        self._dirty.discard(name)

    def option_names(self, prefix: str = ''):
        return [n for n in self.conf['Default'] if n.startswith(prefix)]

    def sync(self):
        # No file lock: os.replace() keeps every write atomic and the
        # per-key merge bounds what a concurrent sync can lose.
        if not os.path.isdir(os.path.dirname(self.settings_fname)):
            return
        merged = self.conf
        if not self._dirty_all:
            disk = configparser.ConfigParser()
            try:
                disk.read(self.settings_fname)
            except (configparser.Error, UnicodeDecodeError):
                disk = None
            if disk is not None:
                if 'Default' not in disk:
                    disk['Default'] = {}
                for name in self._dirty:
                    if self.conf.has_option('Default', name):
                        disk.set('Default', name,
                                 self.conf.get('Default', name, raw=True))
                for name in self._removed:
                    disk.remove_option('Default', name)
                merged = disk
        tmp = self.settings_fname + '.tmp.' + str(os.getpid())
        try:
            with open(tmp, 'w') as configfile:
                merged.write(configfile)
            os.replace(tmp, self.settings_fname)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            return
        self._dirty.clear()
        self._removed.clear()
        self._dirty_all = False

    # log_font_size keeps a custom getter: clamp non-positive sizes to 8.
    @property
    def log_font_size(self):
        v = self.value(self.SettingsLogFontSize)
        if v <= 0:
            v = 8
        return v

    @log_font_size.setter
    def log_font_size(self, value):
        self.set_value(self.SettingsLogFontSize, value)