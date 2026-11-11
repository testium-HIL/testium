.. _sec_dialog_value_test_item:

**dialog_value** test items
============================================================

This test item displays a simple dialog asking a question and returning the entered value.

``dialog_value`` test item has the following description format

.. code-block:: yaml
    :caption: example of ``dialog_value`` test item usage

    - dialog_value:
        name: dialog value test item
        question: operator question

Attributes
-------------------

``dialog_value`` has the following specific attributes:

* ``question``: Question to be displayed in the dialog box
* ``default``: default value to place in the dialog form (optional)

Feature
----------------------

The entered value is stored in the global variables under the
``dialog_value`` test item name as key.