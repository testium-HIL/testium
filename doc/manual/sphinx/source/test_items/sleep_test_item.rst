**sleep** test item
============================================================

sleep test item has the following description format

.. code-block:: yaml
    :caption: ``sleep`` test item example usage

    - sleep:
        name: sleep test item
        timeout: 10
        dialog: True

Attributes
---------------

* ``timeout``: sleep duration in second or in relative date format like "2d 5h 31m 3s", which translate into 2 days, 5 hours, 31 minutes and 3 seconds.
* ``dialog``: If set to True, a window showing the remaining time to wait is displayed (optional parameter set to ``False`` by default)