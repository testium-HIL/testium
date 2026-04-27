**group** test item
============================================================

This element is of the following form:

.. code-block:: yaml
    :caption: ``group`` test item usage example

    - group:
        name: Group Item
        condition: <| "$(OS)" == "Linux" |>
        steps:
            - unittest:
                test_file: test_prod_alpha_13.py
                test_method:
                    ...
            - sleep:
                timeout: 10

The ``group`` element is used to manage a sequence of item as a group.

Attributes
--------------------

* The ``steps`` list describes the sequence executed in the group.
  It is a list of any of the `testium` test items,