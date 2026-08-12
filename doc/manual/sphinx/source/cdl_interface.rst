Command Line Interface
======================

.. code-block:: text

    usage: testium.pyw [-h] [--version] [-b] [-c CONFIG_FILE [CONFIG_FILE ...]] [-r] [-l LOG_FILE]
                        [-d DEFINE [DEFINE ...]] [-p REPORT_FILE] [-t {sqlite,json,junit,html,text}]
                        [-n REPORT_PATTERN [REPORT_PATTERN ...]] [-i INCLUDE_PATH [INCLUDE_PATH ...]] [-o] [-g]
                        [test_file]

    positional arguments:
    test_file             the test script file

    optional arguments:
    -h, --help            show this help message and exit
    --version             Returns the version of testium
    -b, --batch-execution
                            Executes the test in batch mode
    -c CONFIG_FILE [CONFIG_FILE ...], --config-file CONFIG_FILE [CONFIG_FILE ...]
    -o, --no-color        Deactivates stdout colors in batch mode
                            Configuration file
    -r, --run-and-close   Runs the test then closes the application
    -l LOG_FILE, --log-file LOG_FILE
                            log file name
    -d DEFINE [DEFINE ...], --define DEFINE [DEFINE ...]
                            Configuration passed to the executed tests.
    -p REPORT_FILE, --report-file REPORT_FILE
                            report file name
    -t {sqlite,json,junit,html,text}, --report-type {sqlite,json,junit,html,text}
                            report file type
    -n REPORT_PATTERN [REPORT_PATTERN ...], --report-pattern REPORT_PATTERN [REPORT_PATTERN ...]
                            report file pattern
    -i INCLUDE_PATH [INCLUDE_PATH ...], --include-path INCLUDE_PATH [INCLUDE_PATH ...]
                            Python modules search path
    -g, --debug           GUI debug mode

``-h, --help``
--------------

Prints the usage message shown above.

``-b, --batch-execution``
-------------------------

Executes the test in text mode. Qt does not need to be installed in this mode.

``-o, --no-color``
------------------

Disables colored output in batch mode.

``-c, --config-file``
---------------------

This option provides configuration file(s) from the command line.
The configuration files format and content is detailed in the :ref:`config files<sec_configuration_files>` section.

If this parameter is not given while calling *testium*, the default configuration files will be used.

``-r, --run-and-close``
-----------------------

This parameter makes testium close immediately after running the ``test_file`` passed on the command line.

If there is no ``test_file`` argument passed, this option is ignored.

``-l, --log-file``
------------------

Path of the log file for the test execution.
If not provided, the log is written to a temporary folder.

.. _sec_option_define:

``-d, --define``
------------------------------------

Defines one or more variables in the form ``VARIABLE1=value1 VARIABLE2=value2 ..."``.
Then, these variables are available from the test scripts, using the :ref:`global variables<sec_global_variables>`
*testium* feature.

.. _sec_p_param:

``-p, --report-file``
----------------------

Path of the report file, stored during the test execution.

This option is only useful in :ref:`batch mode<sec_batch_mode>`.

``-t, --report-type``
---------------------

This option is used together with option :ref:`-p<sec_p_param>` and defines
the type of report to generate.

Please read the :ref:`reports<sec_reports>` section for more details on
the possible types of report.

``-n, --report-pattern``
-------------------------

This option is used in conjunction with option :ref:`-p<sec_p_param>` and defines
the report pattern(s) used to filter the report results which will be
included in the report file.

More details in :ref:`reports<sec_reports>` section.

``-i, --include-path``
----------------------

Additional Python paths. These paths are appended to the
`sys.path <https://docs.python.org/3/library/sys.html?highlight=sys%20path#sys.path/>`_ python
variable.


``-g, --dev-debug``
-------------------

Development option: attaches a debugger to *testium* itself. See
``CONTRIBUTING.md`` of the source repository. Not used for debugging
tests; see the :ref:`Debugging your tests<sec_debugging>` chapter.