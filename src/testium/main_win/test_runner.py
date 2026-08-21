# Compatibility shim: the run logic moved to gui/run_presenter.py.
from gui.run_presenter import RunPresenter as TestRunner  # noqa: F401
from gui.run_presenter import TestState  # noqa: F401
