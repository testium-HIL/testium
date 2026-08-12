.. _sec_report_test_item:

**report** test item
============================================================

This test item exports report files **during** the test run, from the data
collected so far. It snapshots partial results in a long campaign.

It requires a ``report`` element at the root of the main test file (see the
:ref:`Reports chapter<sec_reports>`).

.. code-block:: yaml
    :caption: ``report`` test item usage example

    - report:
        name: Intermediate report
        export:
            - junit:
                path: $(home)/reports
                file_name: intermediate.xml
                pattern:
                    - Unittest%
            - text:
                path: $(home)/reports
                file_name: report-key-1.txt
                key:
                    - report-key-1

Attributes
---------------------

Besides the :ref:`common attributes<sec_item_common>`, the ``report`` test
item has one specific attribute:

* ``export``: required. One export entry or a list of them, with exactly the
  same syntax and attributes (``path``, ``file_name``, ``pattern``, ``key``,
  ``cmd``) as the root-level ``export``; see
  :ref:`export attributes<sec_reports_attributes>`. All formats are
  available: :ref:`built-ins<sec_reports_builtin>`, the
  :ref:`command export<sec_reports_command>` and installed
  :ref:`plugins<sec_reports_plugins>`.

Notes:

* a ``sqlite`` entry is ignored here: the database storage is configured
  once, in the root ``report`` element;
* exports run with ``no_header`` set: the produced files carry the test
  rows without the run header (the run is not finished, so the global
  result and duration do not exist yet).
