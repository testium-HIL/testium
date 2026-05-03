.. _sec_python_helper_library:

Python helper library
======================

A python library including helper function for python modules called from
testium ``py_func`` items.

User scripts run inside the ``py_func`` subprocess and interact with testium
through a JSON-RPC bridge — the ``py_func.tm`` module. They must **not**
import ``api.testium`` or ``interpreter.*`` directly: those are main-process
modules and may not even be reachable in a packaged build (PyInstaller, .deb).

To include the support of this library in a python script, the following
line must be included in the script header:

.. code-block:: python
   :caption: testium helper library import

    import py_func.tm as tm

.. _sec_global_variables_helpers:

Global variables helper functions
----------------------------------
To manage values in the global variables dataset:

.. automodule:: py_func.tm
   :members: gd, setgd, delgd
   :undoc-members:
   :no-index:

Plot helper functions
------------------------

Add values to a running plot or read the last value from it:

.. automodule:: py_func.tm
   :members: add_plot_values, last_plot_value
   :undoc-members:
   :no-index:

Console and plot **lifecycle** management (``add_console``, ``remove_console``,
``console``, ``add_plot``, ``remove_plot``, ``plot``) is performed by the
``console`` and ``plot`` test items themselves — not from user ``py_func``
scripts. Use those test items to open/close consoles and plots.

Other helper functions
------------------------

.. automodule:: py_func.tm
   :members: OS, get_main_dir, init_timestamp, timestamp, timestamp_as_sec, text_mode
   :undoc-members:
   :no-index:

Debug mode
------------------------

The ``test_debug`` global variable controls debug-only output. Read or write
it via ``tm.gd("test_debug")`` / ``tm.setgd("test_debug", True)``.
