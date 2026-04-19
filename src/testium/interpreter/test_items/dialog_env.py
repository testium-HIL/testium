"""Qt platform environment setup for dialog subprocesses.

Call setup() at the start of every dialog subprocess main() function
to ensure the correct Qt platform plugin is selected.
"""
import sys
import os


def setup():
    """Configure the Qt environment for dialog subprocess usage."""
    if sys.platform.startswith('linux'):
        # On Linux/Wayland, force X11 (via XWayland) to avoid crashes
        # when Qt is initialized inside a multiprocessing subprocess.
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
