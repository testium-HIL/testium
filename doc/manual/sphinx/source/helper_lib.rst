.. _sec_python_helper_library:

Python helper library
======================

A python library including helper function for python modules called from
testium.

To include the support of this library in a python script, the following
line must be included in the script header:

.. code-block:: python
   :caption: testium helper library import

    import py_func.tm as tm

.. _sec_global_variables_helpers:

Global variables helper functions
----------------------------------
To manage values in the global variables dataset, the following testium library API
must be used:

.. automodule:: py_func.tm
   :members: gd, setgd, delgd
   :undoc-members:
   :no-index:

Console helper functions
------------------------

Every opened console instance is added to a list with the
key ``console_instances`` of the global variables.

The instance is removed from the list on close step of the ``console`` test item.

To manage consoles from within ``py_func`` python functions,
the following testium library API can be used:

.. automodule:: libs.testium
   :members: add_console, remove_console, console
   :undoc-members:
   :no-index:

Plot helper functions
------------------------

Every opened plot window instance is added to a list with the
key ``plot_instances`` of the global variables.

The instance is removed from the list on close step of the ``plot`` test item.

To manage plots from within ``py_func`` python functions,
the following testium library API can be used:

.. automodule:: libs.testium
   :members: add_plot, remove_plot, plot, add_plot_values, last_plot_value
   :undoc-members:
   :no-index:

Other helper functions
------------------------

.. automodule:: libs.testium
   :members: OS, get_main_dir, timestamp, timestamp_as_sec
   :undoc-members:
   :no-index:

Debug mode
------------------------

.. automodule:: libs.testium
   :members: debug_enabled, enable_debug, print_debug, print_info, print_warn
   :undoc-members:
   :no-index:
