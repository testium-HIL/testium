.. _sec_debugging:

Debugging your tests
====================

testium provides four complementary tools to debug a test campaign:
breakpoints and step-by-step execution to control the flow, the
variables window to inspect the data, the Debug output switch for
verbose diagnostics, and an IDE debugger attach for the Python code of
``py_func`` items.

Breakpoints
^^^^^^^^^^^

Double-click in the first column of the test tree (left of the
checkboxes) to set or remove a breakpoint — a red dot. The run pauses
before executing a marked item. Breakpoints follow the item across
Refresh and testium restarts, and are dropped when a different file is
loaded.

Step-by-step execution
^^^^^^^^^^^^^^^^^^^^^^

The Run toolbar (also the Test menu) drives the execution. The step
buttons and their shortcuts appear when the **Debug** button is enabled:

* **F5** — start, pause or resume; **Shift+F5** — stop;
* **F10** — step over: run to the next item at the same level;
* **F11** — step into: run to the next item at any depth. From idle, it
  starts the run paused on the first item;
* **Shift+F11** — step out: run to the end of the current level, pause
  one level up.

While paused, the green line marks the current item.

Inspecting variables
^^^^^^^^^^^^^^^^^^^^

**F1** opens the variables window: the global dictionary, filterable,
editable while the test is paused or between runs.

Debug output
^^^^^^^^^^^^

The **Debug** button of the Run toolbar (**Ctrl+Shift+D**) enables the
verbose diagnostics: the ``DEBUG`` log lines, including the remedy hints
attached to some warnings. It drives the ``test_debug`` global variable,
takes effect immediately — even during a run — and keeps its value
between runs and between testium sessions.

A ``test_debug`` value set in a configuration file or with
``-d test_debug`` overrides the button state at load; the button then
shows the effective value. In batch mode, use ``-d test_debug``.

Debugging ``py_func`` code
^^^^^^^^^^^^^^^^^^^^^^^^^^

The Python functions of ``py_func`` items can be debugged from your IDE
(breakpoints in your ``.py`` file, stepping, variable inspection). Two
ways to arm it:

* right-click the ``py_func`` item in the tree → **Wait for IDE
  debugger**. A blue dot marks the item; the request lasts for the
  session only (a Refresh clears it);
* or set ``debug: true`` on the item in the ``.tum`` file.

At the next run, the item waits for a debugger to attach on
``localhost:5678`` (global ``py_func_debug_port``) before calling the
function. Details and IDE configuration: the
:ref:`py_func chapter<sec_py_func_debug>` and the step-by-step tutorial
``doc/debug_tutorial.md`` of the source repository.
