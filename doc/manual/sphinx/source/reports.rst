.. _sec_reports:

Reports
---------

If a report is required (in addition to the log), the ``report`` YAML element
must be added at the root of the TUM main test file.

The ``report`` YAML element has the following form:

.. code-block:: yaml
    :caption: reports global settings

    report:
        enabled: True
        file_name: $(test_name).rep
        path: $(home)/reports
        pattern: "Console%"
        export: junit
        log_stored: False

.. table:: report attributes
    :widths: 20, 30, 50

    +-----------------+-----------------------+-------------------------------------------+
    | Attribute       | default value         | Description                               |
    +-----------------+-----------------------+-------------------------------------------+
    | ``enabled``     | ``True``              | Report activated                          |
    +-----------------+-----------------------+-------------------------------------------+
    | ``file_name``   | /                     | Report file name                          |
    +-----------------+-----------------------+-------------------------------------------+
    | ``path``        | ``$(report_path)``    | Report storage path By default, it uses   |
    |                 |                       | the default one set in the                |
    |                 |                       | preferences.                              |
    +-----------------+-----------------------+-------------------------------------------+
    | ``pattern``     | /                     | The pattern in SQL wildachars syntax      |
    |                 |                       | to be applied on test names to            |
    |                 |                       | selected reported tests.                  |
    +-----------------+-----------------------+-------------------------------------------+
    | ``export``      | /                     | The type of export. For exemple junit.    |
    |                 |                       | By default, the sqlite format is          |
    |                 |                       | used to generate reports.                 |
    +-----------------+-----------------------+-------------------------------------------+
    | ``log_stored``  | /                     | Defines if the output log of each         |
    |                 |                       | test is accessible to generate the        |
    |                 |                       | report export.                            |
    +-----------------+-----------------------+-------------------------------------------+
