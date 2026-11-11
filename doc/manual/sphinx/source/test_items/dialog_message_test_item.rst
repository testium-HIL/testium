**dialog_message** test item
============================================================

This test item displays a simple dialog showing a message.
``dialog_message`` test item has the following description format

.. code-block:: yaml
    :caption: example of ``dialog_message`` test item usage

    - dialog_message:
        name: dialog message test item
        question: operator question

Attributes
---------------------

``dialog_message`` has the following specific attribute:

* ``question``: Sentence to be displayed in the dialog box

Feature
---------------------

Displays the message; no value is returned.