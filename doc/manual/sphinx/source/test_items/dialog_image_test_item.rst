**dialog_image** test item
============================================================

This test item displays an image within a dialog box.

``dialog_image`` test item has the following description format

.. code-block:: yaml
    :caption: example of ``dialog_image`` test item usage

    - dialog_image:
        name: dialog image test item
        question: operator question
        filename: imageToBeDisplayed.jpg

Attributes
----------------------

``dialog_image`` has the following specific attributes:

* ``question``: Question to be displayed in the dialog box
* ``filename``: File name of the image to be displayed in the dialog box.

Feature
----------------------

The test returns a ``FAIL`` if the answer is No and ``PASS`` if yes.