**report** test item
============================================================

This test item exports a report file.

To have this functionality activated, a ``report section`` must be defined at the root of the test file.
The root report section is described in :ref:`report<sec_reports>` section.

report test item has the following description format

.. code-block:: yaml
    :caption: ``report`` test item usage example

    - report:
        name: Intermediate report
        export:
            - junit:
                path: $(home)/reports/report-key-1.junit
                pattern:
                    - Unittest%
                key: report-key-1
            - text:
                file_name: report-key-1.txt
                path: $(home)/reports
                key:
                    - report-key-1Attributes

This item is useful to generate intermediate reports in any format other than ``sqlite``. Nevertheless,
if ``sqlite`` export is defined, It won't generate anything.

Attributes
---------------------

``report`` test item has the following specific attributes:

* ``export``: reports to be exported. It is a list of the reports exports to be executed.
  The supported exports are:

  * ``junit``
  * ``json``
  * ``html``
  * text

The export sub-attributes (see example above) may contain the following attributes.

* ``path``: path of the report files directory,
* ``filename``: report file name,
* ``Pattern``: list of the patterns (applied on test names) used to select the
  tests to exportinto the report,
* ``Key``: list of selected keys which are used to select the tests to export
  into the report.
