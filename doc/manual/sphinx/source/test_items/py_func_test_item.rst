.. _sec_py_func_item:

**py_func** test item
============================================================

The ``py_func`` test item is used to execute custom python scripts with the given
input parameters.

There are two modes for executing a ``py_func`` item. The *class* mode and the *function* mode.

class ``py_func`` item
-------------------------

This is the normal way of calling some custom python code.

A class must be defined and derived from ``FunctionItem`` from the ``libs.testium`` module.

From this class it is possible to define some custom reported values with the following API

* ``reportValue(key, value)``: This ``FunctionItem`` method is adding a value added to the report,
* ``reportedValues()``: This ``FunctionItem`` method is retrieving the current report values.

.. code-block:: python
    :caption: ``py_func`` test item implementation example
    :name: scriptFunctionItem.py

    import py_func.tm as tm

    class TestItemPyFunc(tm.FunctionItem)

        def exec(param1, param2, param4, param4):
            ...
            self.reportValue('my_reported_value', reported_value)
            print(self.reportedValues())
            return 10

The ``exec`` method of the ``FunctionItem`` derived class is executed while running the ``py_func`` test item.

.. code-block:: yaml
    :caption: legacy ``py_func`` test item implementation

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

    def dummy_func(param1, param2, param4, param4):
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

Beside common test items attributes, ``py_func`` item has specific attribute,
some of which being mandatory.

* ``file``: the script file name that contains the function to be executed.
  Only python script format is supported.
* ``func_name``: The function name to be executed.
* ``param``: This is a list of parameters that are passed to the function
  in the order they are presented in the script. These parameters are not
  mandatory and are highly dependent of the function prototype.
* ``context_id``: Optional. When set, all ``py_func`` items sharing the same
  ``context_id`` value run inside the same persistent Python subprocess for the
  duration of the test. See :ref:`py_func context<sec_py_func_context>` for details.

.. code-block:: yaml
    :caption: ``py_func`` test item example of usage

    - py_func:
        file: script_name.py
        func_name: methodName
        param:
            - $(my_param)

The result of the function (after eventual post treatment) is stored in the global
variable named ``pfn_<func_name>``
(See :ref:`global variables<sec_global_variables>` for more detail
on how to access to global variables from test items and scripts).

In the example above, the global variable ``$(pfn_function test item)``
would be created at the end of the item execution. It would contain the resulting
value of the funcToBeExecuted python function.

The ``py_func`` will always result ``PASS``, except if the called function raises
and exception or if the ``expected_result`` attribute is used.

.. _sec_py_func_context:

Sharing state between ``py_func`` calls
------------------------------------------

Each ``py_func`` item without a ``context_id`` runs in a dedicated subprocess that
is started and stopped around the call. State cannot be shared between two such
items using module-level variables.

Two mechanisms are available to share data across calls:

**Using the testium global dictionary**

Inside a ``py_func`` script, the ``tm`` module exposes ``tm.setgd`` and ``tm.gd``
to read and write the testium global dictionary of the test process. Values stored
this way are accessible from any subsequent test item (including other ``py_func``
items) without requiring a shared subprocess.

.. code-block:: python
    :caption: sharing a serializable value via the global dictionary

    import py_func.tm as tm

    def produce(val):
        tm.setgd("my_shared_value", val)
        return val

    def consume():
        return tm.gd("my_shared_value", None)

Values stored with ``tm.setgd`` must be JSON-serializable (str, int, float, list,
dict, bool, None). Non-serializable values (objects, connections, file handles…)
are handled transparently by the local fallback described below.

**Using a shared persistent subprocess (``context_id``)**

When ``context_id`` is set, all ``py_func`` items that share the same identifier
reuse the same subprocess. The subprocess is kept alive until the end of the test.

This is required for non-JSON-serializable objects (e.g. a socket connection, a
device handle). Calling ``tm.setgd`` with such a value stores it inside the
subprocess local dictionary instead of sending it to the main process. It can then
be retrieved with ``tm.gd`` from any subsequent call that runs in the same subprocess.

.. code-block:: python
    :caption: sharing a non-serializable object via ``context_id``

    import py_func.tm as tm

    class _Connection:          # not JSON-serializable
        def __init__(self):
            self.value = "open"

    def open_connection():
        tm.setgd("conn", _Connection())   # stored locally in the subprocess
        return "ok"

    def use_connection():
        conn = tm.gd("conn")              # retrieved from the subprocess local dict
        return conn.value

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

**Python Interpreter environment setup**

Some global variables have an impact on the ``py_func`` test item behavior:

* ``python_bin``: This optional global variable can be used to define
  the python executable path. If not defined, the python interpreter is
  searched in at the default places in the system.
* ``python_env``: This global variable can be used to define
  environment variables for the lua script execution environment.
  Only `PATH` and `PYTHONPATH` are supported.

  .. code-block:: yaml
      :caption: example of configuration file: param.yaml

      [...]
      python_env:
        PATH: "/my/path/"
        PYTHONPATH: "/my/python/modules/"
      [...]