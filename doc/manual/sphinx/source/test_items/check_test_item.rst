**check** test item
============================================================

The ``check`` test item returns the result of a python string evaluation:

.. code-block:: yaml
    :caption: example of ``check`` test item usage

    - check:
        name: check test item example
        values:
            - '"tictactoe" in "$(my_global_string)"'