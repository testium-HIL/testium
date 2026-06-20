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
  Only Lua script format is supported.
* ``func_name``: The function name to be executed.
* ``param``: This is a list of parameters that are passed to the function
  in the order they are presented in the script. These parameters are not
  mandatory and are highly dependent of the function prototype.
* ``context_id``: Optional. When set, all ``lua_func`` items sharing the same
  ``context_id`` value run inside the same persistent Lua subprocess for the
  duration of the test. See :ref:`lua_func context<sec_lua_func_context>` for details.

.. code-block:: yaml
    :caption: ``lua_func`` test item example of usage

    - lua_func:
        name: activity
        file: script_name.lua
        func_name: methodName
        param:
            - $(my_param)

The result of the function (after eventual post treatment) is stored in the global
variable named ``lfn_<item_name>``
(See :ref:`global variables<sec_global_variables>` for more detail
on how to access to global variables from test items and scripts).

In the example above, the global variable ``$(lfn_activity)``
would be created at the end of the item execution. It would contain the resulting
value of the methodName Lua function.

The ``lua_func`` will always result ``PASS``, except if the called function raises
an exception or if the ``expected_result`` attribute is used.

If the called function returns several values, they are kept as a list in the
result; a single return value stays a scalar.

.. _sec_lua_func_context:

Sharing state between ``lua_func`` calls
------------------------------------------

Each ``lua_func`` item without a ``context_id`` runs in a dedicated subprocess that
is started and stopped around the call. Module-level variables are not preserved
between two such items.

Inside a ``lua_func`` script, the ``tm`` module exposes ``tm.setgd`` and ``tm.gd``
to read and write the testium global dictionary of the test process. Values stored
this way are accessible from any subsequent test item without requiring a shared
subprocess.

.. code-block:: lua
    :caption: sharing a value via the global dictionary

    local tm = require("tm")
    local module = {}

    function module.produce(val)
        tm.setgd("my_shared_value", val)
        return val
    end

    function module.consume()
        return tm.gd("my_shared_value")
    end

    return module

When ``context_id`` is set, all ``lua_func`` items that share the same identifier
reuse the same persistent subprocess. This allows Lua-side state (upvalues, module
cache) to be retained across calls beyond what ``tm.setgd`` persists.

.. code-block:: yaml
    :caption: ``lua_func`` items sharing a persistent subprocess

    - lua_func:
        name: produce value
        file: my_script.lua
        func_name: produce
        context_id: my_context
        param:
            - hello

    - lua_func:
        name: consume value
        file: my_script.lua
        func_name: consume
        context_id: my_context
        expected_result: hello

The shared subprocess is automatically stopped at the end of the test run.

**Lua Interpreter environment setup**

Some global variables have an impact on the ``lua_func`` test item behavior:

* ``lua_bin``: This optional global variable can be used to define
  the lua executable path. If not defined, the lua interpreter is
  searched in at the default place in the system.
* ``lua_env``: This global variable can be used to define
  environment variables for the lua script execution environment.
  Only `PATH`, `LUA_PATH`, and `LUA_CPATH` are supported.

  .. code-block:: yaml
      :caption: example of configuration file: param.yaml

      [...]
      lua_env:
        PATH: "/my/path/"
        LUA_PATH: "/my/lua/modules/?.lua;;"
        LUA_CPATH: "/my/lua/modules/?.so;;"
      [...]
