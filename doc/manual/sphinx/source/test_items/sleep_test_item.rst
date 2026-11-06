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

* ``timeout``: sleep duration, see :ref:`Duration format<sec_duration_format>`.
* ``dialog``: If set to True, a window showing the remaining time to wait is displayed (optional parameter set to ``False`` by default)

.. _sec_duration_format:

Duration format
---------------

A duration is a number of seconds, or a string with units.

.. code-block:: yaml
    :caption: Duration examples

    timeout: 10
    timeout: 1.5
    timeout: 1m 30s
    timeout: 2d 5h 31m 3s
    timeout: 1.5h

* Units are ``d`` (days), ``h`` (hours), ``m`` (minutes) and ``s`` (seconds), in this order.
* Each unit is optional. Spaces between units are optional.
* Decimal values are accepted. Negative values are refused.
* Any other text fails the item: ``1h30`` and ``5m 3h`` are errors.

The same format applies to the ``period`` of the :ref:`plot periodic action<sec_plot_periodic>`.
