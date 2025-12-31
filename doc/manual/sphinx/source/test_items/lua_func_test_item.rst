.. _sec_lua_func_item:

**lua_func** test item
============================================================

The ``lua_func`` test item is used to execute custom lua 5.4 scripts with the given
input parameters.

The ``lua_func`` test item is of the form:

.. code-block:: lua
    :caption: ``lua_func`` python function example
    :name: script_file.lua

    local module = {}

    function module.dummy_func(param1, param2, param4, param4):
        ...
        return 10

    return module

.. code-block:: yaml
    :caption: corresponding ``lua_func`` tum extract

    - lua_func:
        name: lua function test item
        file: script_file.lua
        func_name: dummy_func
        param:
            - 123
            - 0.123
            - True
            - $(global_dict_key)
        expected_result: 10

**Attributes**

Beside common test items attributes, lua_func item has specific attribute, some of which being mandatory.

* ``file``: the script file name that contains the function to be executed.
  Only python script format is supported.
* ``func_name``: The function name to be executed.
* ``param``: This is a list of parameters that are passed to the function
  in the order they are presented in the script. These parameters are not
  mandatory and are highly dependent of the function prototype.

.. code-block:: yaml
    :caption: ``lua_func`` test item example of usage

    - lua_func:
        name: activity
        file: script_name.lua
        func_name: methodName
        param:
            - $(my_param)

The result of the function (after eventual post treatment) is stored in the global
variable named ``pfn_<func_name>``
(See :ref:`global variables<sec_global_variables>` for more detail
on how to access to global variables from test items and scripts).

In the example above, the global variable ``$(lfn_activity)``
would be created at the end of the item execution. It would contain the resulting
value of the funcToBeExecuted python function.