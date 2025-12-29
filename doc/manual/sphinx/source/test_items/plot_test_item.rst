**plot** test item
============================================================

This test item is used to display runtime values of tests variables or any evolving value in
a independent external window.

The plot window is defined using the ``plot`` test item:

.. code-block:: yaml
    :caption: ``plot`` test item usage example

    - plot:
        name: test name in GUI
        plot_name: plot identifier
        steps:
            - open:
            - add:
                ...


Attributes
----------------------

In addition to common test items attributes, console test item has specific attributes:

* ``plot_name``: plot window instance name.
* ``steps``: a sequence of actions to be applied to the plot window. More than one action can be
  executed in a ``plot`` item.

The plot test item can accept the actions described in further sections.

All the following actions support the ``name`` attribute. The ``name`` is concatenated with
the action type in the *testium* GUI, and recalled in the test log and reports.

``open`` action
----------------------

This action initializes and opens the plot window with the corresponding attributes as defined below.

This action accepts one optional ``path`` parameter defining a path where are stored the
plot lines values in csv format.

.. code-block:: yaml
    :caption: ``plot`` ``open`` action

    - plot:
        name: Open the plot window
        plot_name: plot identifier
        steps:
            - open:
                name: open the plot
                log_path: $(test_directory)/tmp

``close`` action
----------------------

The ``close`` action closes the plot window and removes its from the managed instances of *testium*.

This action does not have mandatory parameters. However, ``close`` optional action parameters are:

* ``wait_dialog_exit``: Boolean value. If set to True, the window
  is kept opened until the user closes it manually.
* ``timeout``: Value expressed in seconds. It is active if the ``wait_dialog_exit`` is set to True.
  If this parameter is defined, and if not closed manually, the dialog window is kept opened until
  the timeout elapses.

.. code-block:: yaml
    :caption: ``plot`` ``close`` action

    - plot:
        name: Closes the plot
        plot_name: plot identifier
        steps:
            - close:
                wait_dialog_exit: True
                timeout: 600

.. note::
    When the ``close`` action is entered, the ``periodic`` plots are stopped.

``add`` action
----------------------

The ``add`` action is used to add a single data to the ``plot`` window.

.. code-block:: yaml
    :caption: ``plot`` ``add`` action

    - plot:
        name: Add to the plot
        plot_name: plot identifier
        steps:
            - add:
                name: add value 1 & 2
                value1: $(loop_index)
                value2: $(loop_index)+2

The parameter of the ``add`` action is a dictionnary of (*key*, *values*) pairs where the *key* is the plot line name and
*value* is the numeric value to add to the plot line.

The *value* content is evaluated as a python statement if not a number, but a string.

``periodic`` action
----------------------

This action allows to specify a python function to be called and which result is used to update the
plot.

``periodic`` plots are updated automatically and don't require further steps in a test sequence, once executed.

``periodic`` action parameters are:

* ``period``: period of the automatic value update.
* ``file``: python file containing the function to call.
* ``func_name``: the name of the python function to be periodicaly called.
* ``eval``: optional parameter allowing post treatment of the function result.

The ``eval`` parameter of the periodic action is a python evaluable string in which the $(result) keywork
is replaced by the actual function call result.

The result of the action must be a dictionnary of (*key*, *values*) pairs where the *key* is the plot line name and
*value* is the numeric value to add to the plot line.

.. code-block:: yaml
    :caption: ``plot`` ``periodic`` action

    - plot:
        name: Add periodic to the plot
        plot_name: plot identifier
        steps:
            - periodic:
                period:         1
                file:           $(test_path)$(psep)plot.py
                func_name:      random_value
                eval:           '{"periodic": $(result)}'


``last_value`` action
----------------------

The ``last_value`` action returns the last values added to the plot (periodicaly or not) into
the global variables entries.

``last_value`` action parameters are:

* ``name``: Optional parameter giving the list of measures to be returned. If
  it is not defined, all the measures are returned.

.. code-block:: yaml
    :caption: ``plot`` ``last_value`` action

    - plot:
        name: Plot measure_1 value
        plot_name: plot identifier
        steps:
            - last_value:
                name: [measure_1]

The result of the action is stored in the global
variable named ``plv_<item_name>`` in the example above, it would be
``$(plv_Plot measure_1 value)``. See :ref:`global variables<sec_global_variables>` for more detail
on how to access to global variables from test items and scripts.


``export`` action
----------------------

The ``export`` action saves the plot window data in various formats to the filesystem.

.. code-block:: yaml
    :caption: ``plot`` ``export`` action

    - plot:
        name: Plot export
        plot_name: plot identifier
        steps:
            - export: $(my_custom_path)/plot_export.pdf
            - export: $(my_custom_path)/plot_export.csv

At the time of writing of this documentation, ``.pdf`` and ``.csv`` files are supported.