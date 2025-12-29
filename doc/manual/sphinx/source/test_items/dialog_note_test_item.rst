**dialog_note** test items
============================================================

This test item displays a simple dialog allowing to enter some text and printing the entered value in logs.

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