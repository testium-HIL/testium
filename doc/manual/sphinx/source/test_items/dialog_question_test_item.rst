**dialog_question** test item
============================================================

This test item displays a simple dialog asking a question and returning
the entered value.

``dialog_question`` test item has the following description format

.. code-block:: yaml
    :caption: example of ``dialog_question`` test item usage

    - dialog_question:
        name: dialog value test item
        question: operator question

Attributes
--------------------

``dialog_question`` has the following specific attribute:

* ``question``: Question to be asked in the dialog box

Feature
----------------------

The test returns a ``FAIL`` if the answer is No and ``PASS`` if yes.