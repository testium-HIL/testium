
import interpreter.utils.constants as cst
import interpreter.utils.settings as prefs

def icon_prefix():
    if not hasattr(prefs, "settings"):
        prefs.init()
    
    if isinstance(prefs.settings.icons_theme, int) and (0 <= prefs.settings.icons_theme < len(cst.ICON_THEMES_PREFIX)):
        return cst.ICON_THEMES_PREFIX[prefs.settings.icons_theme]
    else:
        return cst.ICON_THEMES_PREFIX[0]