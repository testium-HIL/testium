.. _sec_py_func_item:

**py_func** test item
============================================================

The ``py_func`` test item is used to execute custom python scripts with the given
input parameters.

There are two modes for executing a ``py_func`` item. The class mode and the function mode.

class py_func item
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

Beside common test items attributes, py_func item has specific attribute, some of which being mandatory.

* ``file``: the script file name that contains the function to be executed.
  Only python script format is supported.
* ``func_name``: The function name to be executed.
* ``param``: This is a list of parameters that are passed to the function
  in the order they are presented in the script. These parameters are not
  mandatory and are highly dependent of the function prototype.

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