.. _sec_debugging:

Debugging your tests
====================

testium provides four complementary tools to debug a test campaign:
breakpoints and step-by-step execution to control the flow, the
Variables panel to inspect the data, the Debug output switch for
verbose diagnostics, and an IDE debugger attach for the Python code of
``py_func`` items.

Breakpoints
^^^^^^^^^^^

Double-click in the first column of the test tree (left of the
checkboxes), or select the item and press **Space**, to set or remove a
breakpoint, shown as a red dot. The run pauses
before executing a marked item. Breakpoints follow the item across
Refresh and testium restarts, and are stored per test file.

Right-click an item and pick **Breakpoint condition** to pause only when
an expression is true. Plain Python with ``$(var)`` substitution; the
``<| ... |>`` markers are not needed. A conditional breakpoint is shown
as a red ring; the expression appears in its tooltip. An expression that
fails to evaluate pauses anyway, with a WARN.

Step-by-step execution
^^^^^^^^^^^^^^^^^^^^^^

The Run toolbar (also the Test menu) drives the execution. The step
buttons and their shortcuts appear when the **Debug** button is enabled:

* **F5**: start, pause or resume. Pause lets the current step finish
  and stops the run before the next one; **Shift+F5**: stop;
* **F10**: step over, run to the next item at the same level;
* **F11**: step into, run to the next item at any depth. From idle, it
  starts the run paused on the first item;
* **Shift+F11**: step out, run to the end of the current level, pause
  one level up;
* **Shift+F10**: re-run last step, re-execute the step that just ran
  and pause on the next one. On an item holding actions (console, plot,
  json_rpc), the whole item is re-executed.

While paused, the green line marks the current item.

Jump to a step
^^^^^^^^^^^^^^

While paused, right-click any item and pick **Jump to this item**:
execution moves there, forward or backward, and pauses on it. Nothing
in between is executed; on a backward jump the variables keep their
current values. Jumping into or out of a ``parallel`` block is refused.

Editing the run
^^^^^^^^^^^^^^^

The checkboxes stay operative while a test runs: unchecking an item
skips it when its turn comes. The item currently executing is not
affected.

Inspecting variables
^^^^^^^^^^^^^^^^^^^^

**F1** shows the Variables panel: the global dictionary, filterable,
editable while the test is paused or between runs. Editing a variable
also changes the values derived from it (see
:ref:`when values are resolved<sec_resolution_time>`). The panel is a dock
like Log and Test doc: it can be closed, moved to any side, placed
below the tree or tabbed; the View menu and the **Panels** button of
the toolbar bring it back.

The expression field below the table evaluates a Python expression
against the current variables, also while paused on a breakpoint.
``$(var)`` is substituted; the ``<| ... |>`` markers are not needed; a
lone ``$(var)`` shows the value without evaluating it. It shows the
result, or the error when the expression is invalid. The text is taken
as-is (no YAML quoting rules).

.. _sec_sandbox:

Script sandbox
^^^^^^^^^^^^^^

The **Sandbox** panel runs a Python, Lua or Tcl script against the loaded
test, without adding an item to the sequence. Open it from the View menu
or from the **Panels** button of the toolbar.

.. code-block:: tcl
    :caption: a Tcl script typed in the sandbox

    proc volt {channel} {
        puts "channel $channel"
        return [expr {$channel * 1.5}]
    }
    tm::setgd last_volt [volt 3]
    volt 3

* **Run** (**Ctrl+Enter**) executes the script. The printed text and the
  returned value, or the error with its trace, are shown below the editor.
  They are not written to the test log.
* The script uses the same ``tm`` functions as a function item. ``tm.setgd``
  writes to the variables of the test.
* The state is kept between two runs of the same session: a function
  defined by a script can be called by the next one.
* **Stop** kills the process of a running script.
* **Reset** restarts the process of the session.
* The sandbox is available when the run is stopped or paused. It is
  refused while a run is executing.

Value returned by a script:

* Python: the value of the last line, when it is an expression.
* Lua: the value of the expression, or the values of ``return``.
* Tcl: the result of the last command.

In Python, ``load_file(path)`` imports a script file as a ``py_func`` item
does and returns the module.

**Sessions**

The session list selects the process that runs the script.

* **Sandbox** is a process owned by the panel, one per language.
* The other entries are the ``context_id`` values active for the selected
  language. They are listed only while the run is paused, and only after
  an item of the context has run.

A script run in a ``context_id`` session executes in the process of the
test items of this context. It reads and changes the state left by these
items. The next item of the context sees the changes.

* Tcl: the global variables and the namespaces are visible.
* Lua: the global variables and the modules loaded with ``require`` are
  visible.
* Python: the imported modules are visible. The script file of an item is
  executed again at each call, so its module variables are not kept.

**Stop** and **Reset** on a ``context_id`` session end the process of the
context after a confirmation. The next item of the context starts a new
process.

**Script files**

* **File > Open** loads a ``.py``, ``.lua`` or ``.tcl`` file in the editor.
  The language follows the extension.
* **File > Test scripts** lists the script files used by the function items
  of the test.
* **File > Save** writes the open file. A confirmation is asked when the
  file is used by the test. **File > Save as** writes the editor content to
  a new file.
* **Send to sandbox**, in the context menu of a ``py_func``, ``lua_func``
  or ``tcl_func`` item, fills the editor with the content of the script
  file, followed by the call of the function with the expanded
  parameters. The editor is not attached to the file: **File > Save**
  asks for a path. When a parameter uses a variable that is set later by the
  test, the editor is not changed and the missing variables are listed:
  pause the run on the item, then send it again.

**Editor**

* The syntax of the three languages is highlighted.
* **Ctrl+Space** proposes completions: the keywords, the ``tm`` functions
  and the names defined in the process of the session. Inside
  ``tm.gd("`` or ``tm::gd``, the names of the test variables are proposed.

Debug output
^^^^^^^^^^^^

The **Debug** button of the Run toolbar (**Ctrl+Shift+D**) enables the
verbose diagnostics: the ``DEBUG`` log lines, including the remedy hints
attached to some warnings. It drives the ``test_debug`` global variable,
takes effect immediately, even during a run, and keeps its value
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
``localhost:5678`` (global ``py_func_debug_port``; if busy, the next
free port is used and announced in the log) before calling the
function. Details and IDE configuration: the
:ref:`py_func chapter<sec_py_func_debug>` and the step-by-step tutorial
``doc/debug_tutorial.md`` of the source repository.
