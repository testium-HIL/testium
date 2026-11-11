**dialog_note** test items
============================================================

This test item displays a simple dialog that lets the operator enter text, and prints the entered text in the logs.

``dialog_note`` test item has the following description format

.. code-block:: yaml
    :caption: example of ``dialog_note`` test item usage

    - dialog_note:
        name: dialog value test item
        question: operator question

Attributes
-----------------

``dialog_note`` has the following specific attribute:

* ``question``: Question to be displayed in the dialog box

Feature
--------------------

Prints the entered text in the log.