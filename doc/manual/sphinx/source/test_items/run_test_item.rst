**run** test item
============================================================

This test item executes a new instance of testium.

.. code-block:: yaml
    :caption: ``run`` test item usage example

    - run:
        name: Execute TUM
        tum: example_cycle.tum
        python_bin: python3
        log_file: $(home)/reports/test.log
        report_file: $(home)/reports/test.rep

Attributes
---------------------

run test item has the following specific attributes:

* ``tum``: mandatory the path of the file to execute, it can be relative to current execution folder,
* ``param_file`` (optional) the path of the parameter file to use, otherwise default parameter file is used.
* ``python_bin`` (optional) the path of a specific python to run your scripts,
* ``testium_path`` (optional) the path of a specific testium to run your scripts,
* ``log_file`` (optional) the path of log file to register, if not provided a file is created with timestamp at the location of TUM file.
* ``report_file`` (optional), the path of report file to create
* ``start_time`` (optional), start time for the script execution, in HH:MM format.
* ``end_time`` (optional), end time for an execution within a time frame, in HH:MM format.
* ``wait_for_exec`` (optional). True or False, wait to be in the execution window defined by start_time and end_time to run the script.