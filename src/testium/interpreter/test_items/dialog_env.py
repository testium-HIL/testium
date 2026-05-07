"""Qt platform environment setup for dialog subprocesses.

Call setup() at the start of every dialog subprocess main() function
to ensure the correct Qt platform plugin is selected.
"""
import sys
import os


def setup():
    """Configure the Qt environment for dialog subprocess usage."""
    if sys.platform.startswith('linux'):
        if os.environ.get('DISPLAY'):
            # X11 available: force xcb to avoid crashes in multiprocessing subprocesses.
            os.environ['QT_QPA_PLATFORM'] = 'xcb'
        elif os.environ.get('WAYLAND_DISPLAY'):
            os.environ['QT_QPA_PLATFORM'] = 'wayland'
