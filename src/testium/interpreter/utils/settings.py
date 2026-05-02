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


class SettingsItem():
    def __init__(self, name: str, item_type: type) -> None:
        self.name = name
        self.t = item_type


class TestiumSettings():
    SettingsRecentFiles = SettingsItem('recentFileList', list)
    SettingsLastLogFile = SettingsItem('lastLogFile', str)
    SettingsLogFileSaved = SettingsItem('logFileSaved', bool)
    SettingsHideDocPane = SettingsItem('docPaneHidden', bool)
    SettingsHideLogPane = SettingsItem('logPaneHidden', bool)
    SettingsShowCheckboxes = SettingsItem('checkBoxesShow', bool)
    SettingsLogPath = SettingsItem('defaultLogPath', str)
    SettingsReportPath = SettingsItem('defaultReportPath', str)
    SettingsShowTimeColumn = SettingsItem('showTimeColumn', bool)
    SettingsColumnsSize = SettingsItem('columnsSize', dict)
    SettingsDblClickEnabled = SettingsItem('dblClickEnabled', bool)
    SettingsIconsTheme = SettingsItem('iconsTheme', int)
    SettingsLogFont = SettingsItem('logFont', str)
    SettingsLogFontSize = SettingsItem('logFontSize', int)
    SettingsGitSupported = SettingsItem('logGitSupported', bool)
    SettingsPythonPath = SettingsItem('pythonPath', str)
    SettingsLuaPath = SettingsItem('luaPath', str)

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

    def value(self, key: SettingsItem, default=''):
        if not isinstance(key, SettingsItem):
            raise ETUMRuntimeError('Not a proper Settings item.')
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
                ba = json.loads(self.conf.get(
                    'Default', key.name, fallback=default))
                ret = bytearray(ba)
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

# SettingsRecentFiles = 'recentFileList'
    @property
    def recent_files(self):
        return self.value(self.SettingsRecentFiles, [])

    @recent_files.setter
    def recent_files(self, value):
        self.set_value(self.SettingsRecentFiles, value)

# SettingsLastLogFile = 'lastLogFile'
    @property
    def log_file(self):
        return self.value(self.SettingsLastLogFile)

    @log_file.setter
    def log_file(self, value):
        self.set_value(self.SettingsLastLogFile, value)

# SettingsLogFileSaved = 'logFileSaved'
    @property
    def log_file_saved(self):
        return self.value(self.SettingsLogFileSaved, False)

    @log_file_saved.setter
    def log_file_saved(self, value):
        self.set_value(self.SettingsLogFileSaved, value)

# SettingsHideDocPane = 'docPaneHidden'
    @property
    def hide_doc_pane(self):
        return self.value(self.SettingsHideDocPane, False)

    @hide_doc_pane.setter
    def hide_doc_pane(self, value):
        self.set_value(self.SettingsHideDocPane, value)

# SettingsHideLogPane = 'logPaneHidden'
    @property
    def hide_log_pane(self):
        return self.value(self.SettingsHideLogPane, False)

    @hide_log_pane.setter
    def hide_log_pane(self, value):
        self.set_value(self.SettingsHideLogPane, value)

# SettingsShowCheckboxes = 'checkBoxesShow'
    @property
    def show_checkboxes(self):
        return self.value(self.SettingsShowCheckboxes, False)

    @show_checkboxes.setter
    def show_checkboxes(self, value):
        self.set_value(self.SettingsShowCheckboxes, value)

# SettingsLogPath = 'defaultLogPath'
    @property
    def log_path(self):
        return self.value(self.SettingsLogPath, '$(test_directory)')

    @log_path.setter
    def log_path(self, value):
        self.set_value(self.SettingsLogPath, value)

# SettingsReportPath = 'defaultReportPath'
    @property
    def report_path(self):
        return self.value(self.SettingsReportPath, '$(home)')

    @report_path.setter
    def report_path(self, value):
        self.set_value(self.SettingsReportPath, value)

# SettingsShowTimeColumn = 'showTimeColumn'
    @property
    def show_time_column(self):
        return self.value(self.SettingsShowTimeColumn, False)

    @show_time_column.setter
    def show_time_column(self, value):
        self.set_value(self.SettingsShowTimeColumn, value)

# SettingsColumnsSize = 'columnsSize'
    @property
    def columns_size(self):
        return self.value(self.SettingsColumnsSize, {})

    @columns_size.setter
    def columns_size(self, value):
        self.set_value(self.SettingsColumnsSize, value)

# SettingsDblClickEnabled = 'dblClickEnabled'
    @property
    def dbl_click_enabled(self):
        return self.value(self.SettingsDblClickEnabled, False)

    @dbl_click_enabled.setter
    def dbl_click_enabled(self, value):
        self.set_value(self.SettingsDblClickEnabled, value)

# SettingsIconsTheme = 'iconsTheme'
    @property
    def icons_theme(self):
        return self.value(self.SettingsIconsTheme, 0)

    @icons_theme.setter
    def icons_theme(self, value):
        self.set_value(self.SettingsIconsTheme, value)

# SettingsLogFont = 'logFont'
    @property
    def log_font(self):
        return self.value(self.SettingsLogFont, 'Monospace')

    @log_font.setter
    def log_font(self, value):
        self.set_value(self.SettingsLogFont, value)

# SettingsLogFontSize = 'logFontSize'
    @property
    def log_font_size(self):
        v = self.value(self.SettingsLogFontSize, 8)
        if v <= 0:
            v = 8
        return v

    @log_font_size.setter
    def log_font_size(self, value):
        self.set_value(self.SettingsLogFontSize, value)

# SettingsGitSupported = 'gitSupported'
    @property
    def git_supported(self):
        r = self.value(self.SettingsGitSupported, True)
        return r

    @git_supported.setter
    def git_supported(self, value):
        self.set_value(self.SettingsGitSupported, value)

# SettingsPythonPath = 'python_bin'
    @property
    def python_bin(self):
        r = self.value(self.SettingsPythonPath, "")
        return r

    @python_bin.setter
    def python_bin(self, value):
        self.set_value(self.SettingsPythonPath, value)

# SettingsLuaPath = 'luaPath'
    @property
    def lua_bin(self):
        r = self.value(self.SettingsLuaPath, "")
        return r

    @lua_bin.setter
    def lua_bin(self, value):
        self.set_value(self.SettingsLuaPath, value)