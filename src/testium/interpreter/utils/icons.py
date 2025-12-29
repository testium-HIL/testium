
import interpreter.utils.constants as cst
import interpreter.utils.settings as prefs

def icon_prefix():
    if not hasattr(prefs, "settings"):
        prefs.init()
    return cst.ICON_THEMES_PREFIX[1] if prefs.settings.icons_theme != 0 else cst.ICON_THEMES_PREFIX[0]