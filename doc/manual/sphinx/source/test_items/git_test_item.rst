**git** test item
============================================================

Git test item allows
this item has the following description format

.. code-block:: yaml
    :caption: ``git`` test item usage example

    - git:
        name: git test item
        repo: [$(test_directory), "/path_to/another/repo"]

Attributes
-----------------

* ``repo``: a string or list of string path to the root of the git repositery(ies) to follow.