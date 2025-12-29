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

``dialog_value`` has the following specific attribute:

* ``question``: Question to be displayed in the dialog box
* ``default``: default value to place in the dialog form (optional)

Feature
----------------------

The returned value is added in the global variable entry with the key being the
``dialog_value`` test item name.