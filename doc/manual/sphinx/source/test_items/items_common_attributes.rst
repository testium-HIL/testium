.. _sec_item_common:

Items common attributes
============================================================

All test items have common attributes independently of their types, which are
listed in next table, those are all optional parameters and their default value
if not provided is given in the table as well.

.. table:: test items common attributes
    :widths: 25, 15, 60

    +-----------------------+-------------------+-------------------------------------------------------+
    | **Parameter name**    | **Default value** | **Description**                                       |
    +-----------------------+-------------------+-------------------------------------------------------+
    |``name``               | test item type    | This is the test item name as displayed               |
    |                       |                   | in the test tree window of the                        |
    |                       |                   | testium.                                              |
    |                       |                   |                                                       |
    |                       |                   | This attribute is also supported by actions of        |
    |                       |                   | ``console``, ``jsonrpc`` or ``plot``  test items.     |
    |                       |                   |                                                       |
    |                       |                   | Default value, if not provided, is the                |
    |                       |                   | test item type.                                       |
    +-----------------------+-------------------+-------------------------------------------------------+
    |``stop_on_failure``    |``False``          | If ``stop_on_failure`` is set to                      |
    |                       |                   | ``True``, the test sequence execution                 |
    |                       |                   | stops on test tem failure and no                      |
    |                       |                   | further test items are executed,                      |
    |                       |                   | except those withexecute_on_stop                      |
    |                       |                   | attribute set (see below)                             |
    |                       |                   |                                                       |
    |                       |                   | It depends on the test item to take it                |
    |                       |                   | into account or not.                                  |
    |                       |                   | For example it makes sense to use it                  |
    |                       |                   | for ``unittest_file`` test type                       |
    |                       |                   | because it  can contain many sub-tests,               |
    |                       |                   | but not for sleep test type.                          |
    |                       |                   | In cycles, it means that the child                    |
    |                       |                   | sequence execution is stopped at first                |
    |                       |                   | failure. It also means that the                       |
    |                       |                   | remaining loops are not executed.                     |
    +-----------------------+-------------------+-------------------------------------------------------+
    |``execute_on_stop``    |``False``          | When this attribute is set to True, the               |
    |                       |                   | test item is always run, even on test                 |
    |                       |                   | failure of any test before.                           |
    |                       |                   | This feature is useful, to end the                    |
    |                       |                   | test                                                  |
    |                       |                   | sequence properly on test failure                     |
    |                       |                   | (switch off power supplies, climatic                  |
    |                       |                   | chamber temperature set to ambient                    |
    |                       |                   | temperature….)                                        |
    +-----------------------+-------------------+-------------------------------------------------------+
    |``skipped``            |``False``          | The test item execution is to be                      |
    |                       |                   | skipped during test sequence execution                |
    |                       |                   | if set to ``True``. It will be                        |
    |                       |                   | displayed as failed in the report.                    |
    +-----------------------+-------------------+-------------------------------------------------------+
    | ``no_fail``           | ``False``         | The result of the test step is forced to PASS if this |
    |                       |                   | attribute is set to ``true``.                         |
    +-----------------------+-------------------+-------------------------------------------------------+
    |``doc``                |``""``             | Documentation for the test item that                  |
    |                       |                   | appears in the test doc field and the                 |
    |                       |                   | contextual text window in the testium                 |
    |                       |                   | GUI.                                                  |
    +-----------------------+-------------------+-------------------------------------------------------+
    |``Key``                | /                 | This attribute defines a key which                    |
    |                       |                   | will be attached to the test result and               |
    |                       |                   | which will allow to be filtered during                |
    |                       |                   | the report generation.                                |
    +-----------------------+-------------------+-------------------------------------------------------+
    |``report``             | /                 | This attribute defines values (a dictionary) which    |
    |                       |                   | will be added in the ``data`` field of the report.    |
    +-----------------------+-------------------+-------------------------------------------------------+
    | ``condition``         | /                 | The test item is not executed if its                  |
    |                       |                   | ``condition`` attribute content is                    |
    |                       |                   | evaluated as ``False``.                               |
    |                       |                   | see :ref:`Conditional                                 |
    |                       |                   | execution<sec_conditional_execution>`.                |
    +-----------------------+-------------------+-------------------------------------------------------+
    | ``process_result``    | /                 | Process an evaluation of the process_result           |
    |                       |                   | and store it in the result                            |
    |                       |                   | see :ref:`Process result<sec_process_result>`         |
    |                       |                   | for details.                                          |
    +-----------------------+-------------------+-------------------------------------------------------+
    | ``expected_result``   | /                 | Expected result value or string.                      |
    |                       |                   | see :ref:`Expected result<sec_expected_result>`       |
    |                       |                   | for details.                                          |
    +-----------------------+-------------------+-------------------------------------------------------+


last test result
-----------------------------------------------

The global variable ``last_test_result`` is automatically set at the end of a test item execution.

If the corresponding test item does not return any acutal, the content of the ``last_test_result``
variable will be the test success (``PASS``, ``FAIL`` or ``SKIP``).

It the test item returns a value, the ``last_test_result`` variable will contain the returned value.

The main test items returning a value are:

* :ref:`console<sec_console_test_item>` test item,
* :ref:`jsonrpc<sec_jsonrpc_test_item>` test item,
* :ref:`dialog references<sec_dialog_references_test_item>` test item,
* :ref:`dialog value<sec_dialog_value_test_item>` test item.

Test timings
-----------------------------------------------

After the execution of a test step, the following global variables are set :

* ``ts_start_<item_name>``

* ``ts_end_<item_name>``

and

* duration: ``ts_duration_<item_name>``

See :ref:`global variables<sec_global_variables>` for more detail on how to access to global variables from
test items and scripts.

Skipped test items
-----------------------------------------------

A variable named ``skipped_test_item`` can be defined in the global variable entries
or in configuration file (see :ref:`config files<sec_configuration_files>`) as a list of item to be skipped.

.. _sec_conditional_execution:

Conditional execution
-----------------------------------------------

The ``condition`` attribute content is evaluated as a python string.


.. _sec_process_result:

Process result
-----------------------------------------------

The ``process_result`` attribute can be applied to all the test items. However, it's behavior is different
depending if the test item is returning a value or not.

The ``process_result`` attribute content is evaluated as a python line.

The special ``$(result)`` variable is replaced in the ``process_result`` attribute content with the test result value.

The process result is done before the ``expected_result``

If the result of the evaluation is a boolean, the test will be *PASSED* if ``True``, and *FAIL* otherwise.

.. _sec_expected_result:

Expected result
-----------------------------------------------

The ``expected_result`` attribute can be applied to all the test items. However, it's behavior is different
depending if the test item is returning a value or not.

The test items returning a value are:

* :ref:`dialog_references test item<sec_dialog_references_test_item>`

* :ref:`dialog_value test items<sec_dialog_value_test_item>`

* :ref:`py_func test item<sec_py_func_item>`

* :ref:`dialog_choices test item<sec_dialog_choices_test_item>`

* :ref:`json_rpc test item<sec_jsonrpc_test_item>`

For test items which don't return a value, the ``expected_result`` attribute content is
compared to ``PASS`` or ``FAIL``.

The ``expected_result`` attribute content is a simple comparison with ``$(result)``.

If the result and the expected_result is equal, the test will be *PASSED* if ``True``, and *FAIL* otherwise.

The special ``$(result)`` variable is replaced in the ``expected_result`` attribute content with the test result value.


Export attribute
-----------------------------------------------

.. code-block:: yaml
    :caption: Example of ``export`` common attribute usage

    - check:
        name: Example of result specific to the step 001
        values:
            - $(last_test_result) == PASS
        key:
            - GID-1510554_step_1
        report:
            reported_list: @| random.sample(range(0,20), k=10) |
            reported_float: @| math.sqrt(float(1)) |
            reported_str: This is my reported sentence


.. _sec_item_default_folded:

Container items GUI default folding
============================================================

The container items are items which are the parent of other test items. For example loops and groups
are container test items.

In the GUI, if the user wants that a container test item is folded when he opens a test, the ``.``
character has to be place before the test item declaration.

See an example below:

.. code-block:: yaml
    :caption: example of ``loop`` folded by default in the GUI

    - .loop:
        doc: An example loop
        name: An example loop
    ...