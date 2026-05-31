"""Install a desktop entry + icon under the user's data dir so desktop shells
show the testium icon in the task bar / dock.

On a native Wayland session GNOME takes a window's task-bar icon from the
``.desktop`` file whose name (or ``StartupWMClass``) matches the window
``app_id`` — ``QGuiApplication.setWindowIcon`` is ignored there. The portable
channels (source checkout, PyInstaller binary, AppImage) install no system
desktop file, so we drop an idempotent one in ``~/.local/share``. The window
``app_id`` is set to ``testium`` (see ``QApplication.setDesktopFileName`` in
``testium_win``), which is exactly this file's base name.

Flatpak ships its own ``org.testium.Testium.desktop`` and keeps its own app id,
so the caller skips this integration there.
"""
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

# Must match QApplication.setDesktopFileName(...) for the GUI, and is used as
# both the desktop-file base name and the StartupWMClass.
APP_ID = "testium"


def _launch_command():
    """Best-effort Exec= for the menu entry. Not needed for icon matching, but
    makes the entry actually launchable when possible."""
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        return f'"{appimage}"'
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}"'
    argv0 = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    if argv0 and os.path.exists(argv0):
        return f'"{os.path.abspath(sys.executable)}" "{argv0}"'
    return f'"{os.path.abspath(sys.executable)}" -m testium'


def ensure_desktop_entry():
    """Create (or refresh) ~/.local/share icon + desktop entry. Best-effort:
    any failure is swallowed so it can never take the GUI down.

    Freedesktop-only: a no-op off Linux (Windows / macOS use the window icon)."""
    if not sys.platform.startswith("linux"):
        return
    try:
        data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
        icon_dir = os.path.join(data_home, "icons", "hicolor", "256x256", "apps")
        app_dir = os.path.join(data_home, "applications")
        icon_path = os.path.join(icon_dir, f"{APP_ID}.png")
        desktop_path = os.path.join(app_dir, f"{APP_ID}.desktop")

        os.makedirs(icon_dir, exist_ok=True)
        os.makedirs(app_dir, exist_ok=True)

        # Icon: render the bundled Qt resource to a PNG once. Requires a live
        # QGuiApplication (the caller creates it before calling us).
        if not os.path.isfile(icon_path):
            pixmap = QPixmap(u":/black/testium_logo.png")
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    256, 256,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                pixmap.save(icon_path, "PNG")

        # Absolute Icon= path so the shell resolves it without an icon-cache
        # refresh; StartupWMClass lets X11 / XWayland match too.
        desktop = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Testium\n"
            "Comment=Test sequencer\n"
            f"Icon={icon_path}\n"
            f"Exec={_launch_command()} %f\n"
            "Terminal=false\n"
            f"StartupWMClass={APP_ID}\n"
            "Categories=Utility;Development;\n"
        )

        # Write only when missing or changed, to avoid needless menu churn.
        current = None
        if os.path.isfile(desktop_path):
            with open(desktop_path, "r") as fh:
                current = fh.read()
        if current != desktop:
            with open(desktop_path, "w") as fh:
                fh.write(desktop)
    except Exception:
        # Desktop integration is a nicety, never a hard requirement.
        pass
