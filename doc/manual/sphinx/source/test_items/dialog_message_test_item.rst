**dialog_message** test item
============================================================

This test item displays a simple dialog asking a question and returning the entered value.
dialog_message test item has the following description format

.. code-block:: yaml
    :caption: example of ``dialog_message`` test item usage

    - dialog_message:
        name: dialog value test item
        question: operator question

Attributes
---------------------

``dialog_message`` has the following specific attribute:

* ``question``: Sentence to be displayed in the dialog box
* ``auto_result``: Optional. Outcome used in batch / non-interactive mode.
  If not set, the step fails.

Feature
---------------------

Just display the message.