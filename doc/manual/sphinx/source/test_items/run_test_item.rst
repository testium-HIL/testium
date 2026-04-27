**run** test item
============================================================

This test item executes a new instance of testium with the specified ``.tum`` file.

* In **batch mode** (``-b``): the sub-instance is started with ``-b``.
* In **GUI mode**: the sub-instance is started with ``-r`` (run and close).

The item result is **PASS** if the sub-instance launched and ran to completion,
regardless of whether the sub-tests passed or failed.
It is **FAIL** if the file could not be found, the sub-instance could not be
launched, or the time window was not reached (see ``start_time`` / ``end_time``).

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

* ``tum``: mandatory, the path of the file to execute. Can be relative to the current execution folder.
* ``param_file`` (optional): the path of the parameter file to use; otherwise the default parameter file is used.
* ``python_bin`` (optional): the path of a specific Python interpreter to use.
* ``testium_path`` (optional): the path of a specific testium executable to use.
* ``log_file`` (optional): the path of the log file. In GUI mode, if not provided, a file is created with a timestamp next to the ``.tum`` file. Not used in batch mode.
* ``report_file`` (optional): the path of the report file to create.
* ``start_time`` (optional): earliest time to execute the sub-instance, in ``HH:MM`` format.
* ``end_time`` (optional): latest time for execution within a time frame, in ``HH:MM`` format.
* ``wait_for_exec`` (optional): ``true`` to wait until the time window defined by ``start_time`` and ``end_time`` is reached before running. Requires both ``start_time`` and ``end_time``.