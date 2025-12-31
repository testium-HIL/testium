TUM file syntax
================

*testium* is a python-based tool which uses a ``YAML`` based description file to operate tests: the TUM file.

The description of tests is based on the definition of test sequences. There is a main ``YAML`` element which is the *testium* tool entry point.

All other steps are listed in the step list of the main. Some steps are themselves list of steps as well, such as loop or console items.

``YAML`` is an indented language and parameter encapsulation is defined by their indentation.

``YAML`` language auto detects data type so that it is not necessary to cast the element type explicitly. See `YAML home page <https://yaml.org/>`_ for further information on the language.

The example below shows a basic implementation of the TUM description file:

.. code-block:: yaml
    :caption: main test file

    main:
        name: Test example
        steps:
            - test_item1:
                name: test_1
            - loop :
                name: test cyle
                iterator: 5
                steps:
                    - test_item:
                        name: test_2
                    - test_item:
                        name: test_3


.. _sec_configuration_files:

Configuration files
--------------------

A configuration file can be specified in the .tum file or by the command line.
This configuration file is optional.

It can be of three different syntax:

* XML
* YAML
* JSON

The type of file is recognized by the file name extension (.xml, .yaml, .json).

During the test script loading process, the values defined in these configuration files
are added to the global variables and are then accessible from the test items and scripts
(cf. :ref:`global variables<sec_global_variables>`).

The parameter file can be specified in the .tum file root:

.. code-block:: yaml
    :caption: configuration files definition

    config_file:
        - myparam.xml
        - config1.json
        - config2.yaml

    main:
        name: Test example
        [...]

If nothing is specified, the ``param.xml``, ``param.yaml`` and ``param.json``
are automatically loaded, if present in the test directory.

Files loading
^^^^^^^^^^^^^^^^^^

The ``JSON`` and ``YAML`` configuration files variables are evaluated directly.

The XML files content is evaluated as follows.

.. code-block:: xml
    :name: param.xml

    <?xml version="1.0" ?>
    <root>
        <parameter name="param1" value="['abc', 'bcd']"/>
        <parameter name="param2" value="0x123454"/>
        <parameter name="param3" str="def"/>
    </root>

If the ``parameter`` XML item defines:

* ``value`` argument: its content is parsed for variable substitution
  (see :ref:`variables expansion<sec_variable_expansion>`) and then evaluated as a python statement,
* ``str`` argument: its content is not evaluated and is kept as a string.

.. _sec_global_variables:

Global variables
-------------------

Global variables feature is adding the possibility for test items and test scripts to access a common
and global variables database.

The global variables dataset is populated from various sources:

* the :ref:`command line<sec_option_define>`,
* :ref:`built-in values<sec_global_variables_builtin>`,
* the :ref:`configuration files<sec_configuration_files>`,
* some test items results,
* the :ref:`helper library API<sec_global_variables_helpers>`, accessible from python scripts.

Theses global variables are used for variable expansion in scripts (see :ref:`variables expansion<sec_variable_expansion>`).

Another possible usage of the global variables is to share persistent data between test steps.

A library allowing python functions to access global variables is available from the
python scripts. See details in section :ref:`helper library<sec_python_helper_library>`.

Apart from the value obtained from the param.xml file, the global varibles entries
contains also built-in specific value, and test item specific values.

.. _sec_global_variables_builtin:

Built-in values
^^^^^^^^^^^^^^^^^^^

The following keys are automatically accessible through the testium
library API (see :ref:`helper library<sec_python_helper_library>`)

* ``test_directory``: the absolute path of the directory of the main .tum file,
* ``test_main_file``: the main .tum file,
* ``os``: the name of the platform which is used. Can be Linux or Windows,
* ``host_name``: The name of the host on which testium is running,
* ``home``: home directory of the current user,
* ``testrun_date``: The date when the test has started (as a string) in
  format YYYY-MM-DD,
* ``testrun_time``: The time when the test has started (as a string) in
  format HH:MM:SS,
* ``test_name``: The name of the file being executed without extension,
* ``home``: the path of the current user's home directory,
* ``test_outputs``: list of the paths of the test log and test report (if any),
* ``last_test_result``: test result of the last step (see :ref:`sec_item_common`),
* ``ts_start_<item_name>``: timestamp at the start of test item execution (see :ref:`sec_item_common`),
* ``ts_end_<item_name>``: timestamp at the end of test item execution (see :ref:`sec_item_common`),
* ``ts_duration_<item_name>``: duration of test item execution in seconds (see :ref:`sec_item_common`),
* ``cn_<test_name>``: console test item result (see section :ref:`sec_console_test_item`),
* ``pfn_<func_name>``: py_func test item result (see section :ref:`sec_py_func_item`),
* ``lfn_<func_name>``: lua_func test item result (see section :ref:`sec_lua_func_item`),
* ``cs_<test_name>``: dialog_choices test item result (see section :ref:`sec_dialog_choices_test_item`),
* ``loop_param``: loop iterator (available from within a loop item,
  see :ref:`sec_loop_item`),
* ``loop_index``: loop index (available from within a loop item, see
  :ref:`sec_loop_item`),
* ``loop_count``: loop number (available from within a loop item, see
  :ref:`sec_loop_item`). If the loop number its value is the python constant
  ``inf``.


Test items entries
^^^^^^^^^^^^^^^^^^^^

All test items attributes can be global variable entry;
when using the entry ``$(<global>)`` before a key value, the corresponding
key entry is searched within the global variables dataset.

References
^^^^^^^^^^^^^^

If the ``dialog_references`` test item has been included (see
:ref:`dialog_reference test item<sec_dialog_references_test_item>`), the global
dict will contain the result of this test item in the key ``tested_items``.

Dialog values
^^^^^^^^^^^^^^^^

All dialog returned values are inserted in the global variables entries with the
key value being the test item name attribute (see :ref:`dialog_value test item<sec_dialog_value_test_item>`).

.. _sec_variable_expansion:

Paramers passing, variable expansion and evaluations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the most useful functionalities for scalability and flexibility of the
.tum files is the ability to expanse variables at test runtime.

It is done by replacing any occurrence of ``$(my_global)`` with the content of
the variable in the global variables entries (see :ref:`global variables<sec_global_variables>`).

The variable substitution is recursive and checks all the occurrences of the
``$(x)`` pattern in a string.

It is also possible to perform evaluation of python substrings during parameters passing.
It is done by using the ``<@ expr @>`` pattern in a string.
`expr` may then be a correct python expression.

Below are illustrated simple and more complicated cases of expansion and evaluation depending on
their pattern.

.. code-block:: yaml
    :caption: variables expansion and evaluation

    - let:
        name: Dynamic variables expansion
        key: $(test)_PASS
        values:
            - expanse_select: <@"$(expanse_select)".replace("o", "a")@>
            - expanse_index: $(expanse_index_$(expanse_select))
            - expanse_table: $(expanse_table_$(expanse_select))
            - expanse_eval: <@$(expanse_index) == 1@>

Test Items
--------------------

All *testium* steps are described in sequence as test items in the step
list of the main test item (and eventually of the loop test item).

TUM file ``main`` item is itself a variant of test items with a name and an
step list attributes.



.. toctree::
   :maxdepth: 3
   :caption: Contents:

   test_items/items_common_attributes.rst
   test_items/check_test_item.rst
   test_items/console_test_item.rst
   test_items/dialog_choices_test_item.rst
   test_items/dialog_image_test_item.rst
   test_items/dialog_message_test_item.rst
   test_items/dialog_note_test_item.rst
   test_items/dialog_question_test_item.rst
   test_items/dialog_reference_test_item.rst
   test_items/dialog_value_test_item.rst
   test_items/py_func_test_item.rst
   test_items/git_test_item.rst
   test_items/group_test_item.rst
   test_items/json-rpc_test_item.rst
   test_items/let_test_item.rst
   test_items/loop_test_item.rst
   test_items/lua_func_test_item.rst
   test_items/plot_test_item.rst
   test_items/report_test_item.rst
   test_items/run_test_item.rst
   test_items/sleep_test_item.rst
   test_items/unittest_file_test_item.rst



.. include:: includes.rst

.. include:: templates.rst

.. include:: reports.rst

.. include:: other_features.rst
