**let** test item
============================================================

This element is of the following form:

.. code-block:: yaml
    :caption: ``let`` test item usage example

    - let:
        name: Let Item
        values:
            key1: value1
            key2: value2
            key3: $| $(variable)[$(loop_index)] |

The ``let`` element is used to set values in the global directory.

Attributes
----------------

* The ``values`` list gives the {<key>, <value>} couples to set in the
  global directory,