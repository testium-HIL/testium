.. _sec_loop_item:

**loop** test items
============================================================

This element is of the following form:

.. code-block:: yaml
    :caption: ``loop`` test item usage example

    - loop:
        name: Cycle Temperature
        iterator: 10
        steps:
            - unittest:
                test_file: test_prod_rio6_8093.py
            - py_func:
                name: function test item
                file: scriptTestFile.py
                func_name: funcToBeExecuted
                param:
                    - $(loop_param)
        exit_condition:
            file: script_name.py
            func_name: methodName

The loop element executes repeatedly the ``steps`` sequence of items.

Iteration is controlled by the ``iterator`` attribute, described later in
this chapter.

Attributes
----------------

Below are described loop test item specific attributes.

* ``Iterator``: giving the number of loop iteration (see dedicated chapter below).
* ``steps``: describes the sequence executed at each cycle; it is
  a list of any of the testium test items.
* ``exit_condition``: defines when to exit the loop. If the condition evaluates
  to ``True`` the loop continues; otherwise it stops. exit_condition attributes are:

  * ``time``: the loop stops after the time (in minutes) is elapsed (optional)
  * ``value``: the loop stops when the content of the value attribute is
    True (optional)
  * ``file``: the script file that contains a function executed at each
    iteration. Only python script format is supported (optional
    if another exit_condition attribute is defined)
  * ``func_name``: the function to execute on each loop when the file attribute
    is defined. The function referenced by the ``func_name`` attribute must
    have two parameters: the current loop iterator value and the report,
    even if they are not used. This attribute is mandatory if the file
    attribute is defined.
  * ``eval``: optional parameter allowing post-processing of the function result.
    It is a python evaluable string in which the ``$(result)`` keyword
    is replaced by the actual function call result (see example below).

.. code-block:: yaml
    :caption: ``loop`` exit condition

    - loop:
        ...
        exit_condition:
            file: script_name.py
            func_name: methodName
            eval: $(result) < 2

**Iterator**

The iterator attribute can be of the following types:

* An integer giving the number of iterations,
* A list. The number of elements of the list gives the loop number, and
  the list member are the consecutive loop parameters,
* Undefined. Then cycle loops until the exit condition is reached.

**Loop variables**

The following loop variables are automatically defined:

* ``$(loop_param)``: parameter of the loop. It contains the iterator value.
* ``$(loop_index)``: index of the loop, starting with 0 and incremented at each cycle.
* ``$(loop_index_inverse)``: index counting down, starting from the iteration
  count minus 1 and decremented at each cycle.
* ``$(loop_count)``: loop total iteration number. If the number of loops is undefined
  its value is the python ``inf``.

When these variables are found in a parameter, an attribute, etc, testium
searches the test hierarchy upward for the enclosing loop and substitutes
that loop's value.

If more than one loop exists in the test item hierarchy, the lowest level
loop iterator is used.
