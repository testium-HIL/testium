import os
import configparser
import json
import platform
from runtime.tum_except import ETUMRuntimeError

SettingsCompany = 'Testium'
SettingsApplication = 'testium'


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

    def __init__(self):
        if 'windows' in platform.system().lower():
            user_path = os.getenv('APPDATA')
        else:
            user_path = os.path.join(os.getenv('HOME'), '.config')

        self.settings_fname = os.path.join(user_path, SettingsCompany,
                                           SettingsApplication,
                                           SettingsApplication + '.conf')

        if not os.path.isfile(self.settings_fname):
            try:
                if not os.path.isdir(os.path.dirname(os.path.dirname(self.settings_fname))):
                    os.mkdir(os.path.dirname(os.path.dirname(self.settings_fname)))
                if not os.path.isdir(os.path.dirname(self.settings_fname)):
                    os.mkdir(os.path.dirname(self.settings_fname))
            except FileNotFoundError:
                pass

            if os.path.exists(os.path.dirname(self.settings_fname)):
                with open(self.settings_fname, "x") as fd:
                    pass

        self.conf = configparser.ConfigParser()
        if os.path.isfile(self.settings_fname):
            self.conf.read(self.settings_fname)
        if not 'Default' in self.conf:
            self.clear()

    def clear(self):
        self.conf['Default'] = {}
        self.sync()

    def value(self, key: SettingsItem, default=_UNSET):
        if not isinstance(key, SettingsItem):
            raise ETUMRuntimeError('Not a proper Settings item.')
        if default is _UNSET:
            default = key.default
        if type(default) != key.t:
            raise ETUMRuntimeError(
                'Types mismatch in config file. You could try to erase "{}" to solve the issue'.format(self.settings_fname))
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
                'Types mismatch in config file. You could try to erase "{}" to solve the issue'.format(self.settings_fname))
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

    def sync(self):
        if os.path.isfile(self.settings_fname):
            with open(self.settings_fname, 'w') as configfile:
                if configfile.writable():
                    self.conf.write(configfile)

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