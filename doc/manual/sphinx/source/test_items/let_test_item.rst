**let** test item
============================================================

This element is of the following form:

.. code-block:: yaml
    :caption: ``let`` test item usage example

    - let:
        name: Let Item
        values:
            - key1: value1
            - key2: value2
            - key3: <| $(variable)[$(loop_index)] |>

The ``let`` element is used to set values in the global dictionary.

The values are evaluated when the item runs and the results are stored:
a value derived from another variable does not change when that
variable changes later. Each pair sees the pairs written above it.
Configuration file values behave differently: they are
:ref:`resolved when used<sec_resolution_time>`.

Attributes
----------------

* The ``values`` list gives the {<key>, <value>} pairs to set in the
  global dictionary,
* ``condition``: the item runs only when the expression is true
  (:ref:`common attribute<sec_item_common>`),
* ``key``: expected-result accounting key
  (:ref:`common attribute<sec_item_common>`).