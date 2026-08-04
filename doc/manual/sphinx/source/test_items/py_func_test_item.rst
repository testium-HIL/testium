.. _sec_py_func_item:

**py_func** test item
============================================================

The ``py_func`` test item is used to execute custom python scripts with the given
input parameters.

There are two modes for executing a ``py_func`` item. The *class* mode and the *function* mode.

class ``py_func`` item
-------------------------

This is the normal way of calling some custom python code.

A class must be defined and derived from ``FunctionItem`` from the ``py_func.tm`` module.

From this class it is possible to define some custom reported values with the following API

* ``reportValue(key, value)``: This ``FunctionItem`` method adds a value to the report,
* ``reportedValues()``: This ``FunctionItem`` method returns the values reported so far.

.. code-block:: python
    :caption: ``py_func`` test item implementation example
    :name: scriptFunctionItem.py

    import py_func.tm as tm

    class TestItemPyFunc(tm.FunctionItem):

        def exec(self, param1, param2, param3, param4):
            ...
            self.reportValue('my_reported_value', reported_value)
            print(self.reportedValues())
            return 10

The ``exec`` method of the ``FunctionItem`` derived class is executed while running the ``py_func`` test item.

.. code-block:: yaml
    :caption: class ``py_func`` test item usage

    - py_func:
        name: function test item
        file: scriptTestFile.py
        func_name: TestItemPyFunc
        param:
            - 123
            - 0.123
            - True
            - $(global_dict_key)
        expected_result: 10

**legacy py_func**

The legacy py_func test item is of the form:

.. code-block:: python
    :caption: legacy ``py_func`` python function example
    :name: scriptTestFile.py

    def dummy_func(param1, param2, param3, param4):
        ...
        return 10

There is no possibility to access the report features in that mode.

.. code-block:: yaml
    :caption: corresponding ``py_func`` tum extract

    - py_func:
        name: function test item
        file: scriptTestFile.py
        func_name: funcToBeExecuted
        param:
            - 123
            - 0.123
            - True
            - $(global_dict_key)
        expected_result: 10

**Attributes**

Besides the common test item attributes, the ``py_func`` item has specific attributes;
``file`` and ``func_name`` are mandatory.

* ``file``: the script file name that contains the function to be executed.
  Only python script format is supported.
* ``func_name``: The function name to be executed.
* ``param``: This is a list of parameters that are passed to the function
  in the order they are presented in the script. These parameters are not
  mandatory and depend on the function prototype.
* ``context_id``: Optional. When set, all ``py_func`` items sharing the same
  ``context_id`` value run inside the same persistent Python subprocess for the
  duration of the test. See :ref:`py_func context<sec_py_func_context>` for details.
* ``debug``: Optional. When ``true``, the subprocess waits for a debugger to
  attach before running the function. See
  :ref:`debugging<sec_py_func_debug>` below.

.. code-block:: yaml
    :caption: ``py_func`` test item example of usage

    - py_func:
        file: script_name.py
        func_name: methodName
        param:
            - $(my_param)

The result of the function (after optional post-processing) is stored in the global
variable named ``pfn_<item_name>``
(See :ref:`global variables<sec_global_variables>` for more detail
on how to access to global variables from test items and scripts).

In the example above, the global variable ``$(pfn_function test item)``
would be created at the end of the item execution. It would contain the resulting
value of the funcToBeExecuted python function.

The ``py_func`` result is always ``PASS``, unless the called function raises
an exception or the ``expected_result`` attribute is used.

.. _sec_py_func_context:

Sharing state between ``py_func`` calls
------------------------------------------

Each ``py_func`` item without a ``context_id`` runs in a dedicated subprocess that
is started and stopped around the call. State cannot be shared between two such
items using module-level variables.

Inside a ``py_func`` script, ``tm.setgd`` and ``tm.gd`` read and write the testium
global dictionary. Values stored this way are accessible from any subsequent test
item, including other ``py_func`` items, without requiring a shared subprocess.

.. code-block:: python
    :caption: sharing a value via the global dictionary

    import py_func.tm as tm

    def produce(val):
        tm.setgd("my_shared_value", val)
        return val

    def consume():
        return tm.gd("my_shared_value", None)

When ``context_id`` is set, all ``py_func`` items that share the same identifier
reuse the same persistent subprocess. This allows sharing any Python object across
calls — including objects that cannot be transmitted to other processes.

.. code-block:: python
    :caption: sharing an object via ``context_id``

    import py_func.tm as tm

    def open_connection():
        tm.setgd("conn", MyConnection())
        return "ok"

    def use_connection():
        conn = tm.gd("conn")
        return conn.status()

.. code-block:: yaml
    :caption: ``py_func`` items sharing a persistent subprocess

    - py_func:
        name: open connection
        file: my_script.py
        func_name: open_connection
        context_id: my_context
        expected_result: ok

    - py_func:
        name: use connection
        file: my_script.py
        func_name: use_connection
        context_id: my_context
        expected_result: open

The shared subprocess is automatically stopped at the end of the test run.

.. _sec_py_func_debug:

Debugging your functions
------------------------------------------

Setting ``debug: true`` on a ``py_func`` item lets you debug the function
step by step from your IDE. A step-by-step tutorial is provided in
``doc/debug_tutorial.md`` of the source repository; this section is the
reference. Before calling the function, the subprocess
starts a `debugpy <https://github.com/microsoft/debugpy>`_ listener on
``localhost:5678`` and waits for a debugger to attach; the test log shows::

    py_func waiting for the debugger on localhost:5678 — attach from your IDE, or Stop to cancel

Requirements: install debugpy with the host Python — the ``python_bin``
interpreter, the same one running your functions:

.. code-block:: sh

    <python_bin> -m pip install debugpy

Then attach from the IDE. VSCode configuration (``launch.json``):

.. code-block:: json

    {
        "name": "Attach to py_func",
        "type": "debugpy",
        "request": "attach",
        "connect": {"host": "localhost", "port": 5678},
        "justMyCode": true
    }

Set breakpoints in your ``.py`` file and press F5: once attached, the
function runs and stops on your breakpoints. Notes:

* the run resumes only after the debugger is attached. Stop cancels the
  wait (the item fails); an item left waiting fails after one hour;
* if debugpy is missing or the port cannot be opened, the function is
  not run: the item fails with an explanatory message plus a ``WARN``
  line, and the test run continues;
* the listening port can be changed with the ``py_func_debug_port``
  global variable (configuration file or ``-d py_func_debug_port=<n>``);
* with ``context_id``, the shared subprocess opens the listener once: the
  first ``debug: true`` item fixes the port (a later change is ignored
  with a warning) and the debugger stays attached for the following
  items. If the IDE disconnects, the next ``debug: true`` item waits for
  a new attach;
* the listener only accepts local connections. To debug a testium
  running on a remote machine, open an SSH tunnel:
  ``ssh -L 5678:localhost:5678 <remote>``;
* with the ``redirectOutput`` debugger option, the function's prints may
  appear both in the IDE debug console and in the testium log.

**Python Interpreter environment setup**

Some global variables have an impact on the ``py_func`` test item behavior:

* ``python_bin``: This optional global variable can be used to define
  the python executable path. If not defined, the python interpreter is
  looked up in the default system locations.
* ``python_env``: This global variable can be used to define
  environment variables for the python script execution environment.
  Only `PATH` and `PYTHONPATH` are supported.

  .. code-block:: yaml
      :caption: example of configuration file: param.yaml

      [...]
      python_env:
        PATH: "/my/path/"
        PYTHONPATH: "/my/python/modules/"
      [...]