.. _sec_tcl_func_item:

**tcl_func** test item
============================================================

The ``tcl_func`` test item executes a function of a Tcl script with the given
input parameters. Tcl 8.6 or later is required. No Tcl package is needed.

.. code-block:: tcl
    :caption: ``tcl_func`` Tcl function example
    :name: script_file.tcl

    proc dummy_func {param1 param2 param3 param4} {
        ...
        return 10
    }

.. code-block:: yaml
    :caption: corresponding ``tcl_func`` tum extract

    - tcl_func:
        name: tcl function test item
        file: script_file.tcl
        func_name: dummy_func
        param:
            - 123
            - 0.123
            - True
            - $(global_dict_key)
        expected_result: 10

**Attributes**

Besides the common test item attributes, the ``tcl_func`` item has specific
attributes. ``file`` and ``func_name`` are mandatory. Both are resolved on
every execution: in a loop, a ``$( )`` value can select a different function
per iteration.

* ``file``: the Tcl script that contains the function. A relative path is
  resolved from the test directory. The script is loaded with ``source``
  before each call.
* ``func_name``: the name of the function to call. A namespace is allowed,
  for example ``bench::read_voltage``.
* ``param``: the list of arguments passed to the function, in order.
* ``context_id``: optional. All ``tcl_func`` items with the same
  ``context_id`` run in the same persistent Tcl process. See
  :ref:`tcl_func context<sec_tcl_func_context>`.

The result of the function (after optional post-processing) is stored in the
global variable named ``tfn_<item_name>``
(see :ref:`global variables<sec_global_variables>`).

The ``tcl_func`` result is always ``PASS``, unless the function raises an error
or the ``expected_result`` attribute is used. The error message and the Tcl
call stack are written to the log.

The text written with ``puts`` on ``stdout`` or ``stderr`` goes to the test
log.

.. _sec_tcl_func_types:

Value types
------------------------------------------

Tcl values are strings. testium values are typed. The conversion follows
these rules.

Parameters, from testium to Tcl:

* A number or a string is passed as its text.
* A boolean is passed as ``true`` or ``false``.
* A list is passed as a Tcl list. A dictionary is passed as a Tcl dict.
* ``None`` is passed as an empty string.

Returned values and ``tm::setgd`` values, from Tcl to testium:

* A decimal integer or a decimal number becomes a number.
* ``true`` and ``false`` become booleans.
* An empty string becomes ``None``.
* Any other value becomes a string. A Tcl list or dict is not detected:
  ``a b c`` is the string ``"a b c"``.

The following commands force the type of a value. They can be nested.

* ``tm::list <list>``: a list.
* ``tm::dict <dict>``: a dictionary.
* ``tm::str <value>``: a string, for example ``"12"`` or an empty string.
* ``tm::bool <value>``: a boolean, from any Tcl boolean value.
* ``tm::null``: ``None``.

.. code-block:: tcl
    :caption: returning typed values

    proc measure {} {
        dict set result voltage 3.3
        dict set result serial [tm::str 0012]
        dict set result ok [tm::bool 1]
        dict set result samples [tm::list {1 2 3}]
        return [tm::dict $result]
    }

This function returns ``{'voltage': 3.3, 'serial': '0012', 'ok': True,
'samples': [1, 2, 3]}``.

.. _sec_tcl_func_context:

Sharing state between ``tcl_func`` calls
------------------------------------------

Each ``tcl_func`` item without a ``context_id`` runs in a dedicated process
that is started and stopped around the call. Tcl variables are not
preserved between two such items.

Inside a Tcl script, ``tm::gd``, ``tm::setgd`` and ``tm::delgd`` read, write
and delete the global variables of the test. These values are available to
any later test item.

.. code-block:: tcl
    :caption: sharing a value through the global variables

    proc produce {val} {
        tm::setgd my_shared_value $val
        return $val
    }

    proc consume {} {
        return [tm::gd my_shared_value]
    }

``tm::gd <name> <default>`` returns the default value when the variable
does not exist.

When ``context_id`` is set, all ``tcl_func`` items with the same identifier
reuse the same persistent process. Tcl global variables are then kept
between calls. The script is loaded again before each call: a variable
set at the top level of the script is set again.

.. code-block:: yaml
    :caption: ``tcl_func`` items sharing a persistent process

    - tcl_func:
        name: first call
        file: my_script.tcl
        func_name: count_calls
        context_id: my_context
        expected_result: 1

    - tcl_func:
        name: second call
        file: my_script.tcl
        func_name: count_calls
        context_id: my_context
        expected_result: 2

.. code-block:: tcl
    :caption: my_script.tcl

    proc count_calls {} {
        return [incr ::call_count]
    }

The shared process is stopped at the end of the test run.

**Tcl interpreter setup**

Some global variables change the ``tcl_func`` test item behavior:

* ``tcl_bin``: optional path of the ``tclsh`` executable. If not defined,
  ``tclsh`` is looked up in ``PATH``.
* ``tcl_env``: environment variables of the Tcl process. Only ``PATH`` and
  ``TCLLIBPATH`` are supported.

  .. code-block:: yaml
      :caption: example of configuration file: param.yaml

      [...]
      tcl_bin: /opt/tcl/bin/tclsh9.0
      tcl_env:
        TCLLIBPATH: "/my/tcl/packages"
      [...]

If a test contains a ``tcl_func`` item and no Tcl interpreter is found, the
test is not loaded. The error message lists the names that were tried.
