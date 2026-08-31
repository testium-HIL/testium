# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Preferences: the declarative field table, the store/restore/dirty-set
protocol and the changed-preference -> interface-effect dispatch.
Pure Python; the toolkit side implements PreferencesView and the effect
verbs listed in CHANGE_EFFECTS."""

import interpreter.utils.settings as prefs


def pref_fields():
    """(setting, widget type) per dialog preference; types: bool, text,
    int, combo, font."""
    s = prefs.settings
    return [
        (s.SettingsShowCheckboxes,  "bool"),
        (s.SettingsShowTimeColumn,  "bool"),
        (s.SettingsLogPath,         "text"),
        (s.SettingsReportPath,      "text"),
        (s.SettingsDblClickEnabled, "bool"),
        (s.SettingsEditorCmd,       "text"),
        (s.SettingsIconsTheme,      "combo"),
        (s.SettingsLogFont,         "font"),
        (s.SettingsLogFontSize,     "int"),
        (s.SettingsGitSupported,    "bool"),
        (s.SettingsPythonPath,      "text"),
        (s.SettingsLuaPath,         "text"),
    ]


# Changed preference -> main-window refresh verb, applied on dialog OK.
CHANGE_EFFECTS = [
    ("SettingsShowCheckboxes",  "show_checkboxes"),
    ("SettingsDblClickEnabled", "apply_dbl_click_preference"),
    ("SettingsShowTimeColumn",  "apply_time_column_preference"),
    ("SettingsLogFont",         "prefs_apply_font"),
    ("SettingsLogFontSize",     "prefs_apply_font_size"),
]


def apply_preference_changes(presenter, main_view):
    for attr, verb in CHANGE_EFFECTS:
        if presenter.is_changed(getattr(prefs.settings, attr)):
            getattr(main_view, verb)()


class PreferencesPresenter:
    def __init__(self, view):
        self._view = view
        self._changed = set()

    def store(self):
        """Persist edited values; the dirty set keeps what changed."""
        self._changed = set()
        for key, ftype in pref_fields():
            val = self._view.field_value(key, ftype)
            if val != prefs.settings.value(key):
                prefs.settings.set_value(key, val)
                self._changed.add(key.name)
        prefs.settings.sync()

    def restore(self):
        """Load the stored values into the dialog (open and cancel)."""
        for key, ftype in pref_fields():
            self._view.set_field_value(key, ftype, prefs.settings.value(key))

    def is_changed(self, setting):
        return setting.name in self._changed
