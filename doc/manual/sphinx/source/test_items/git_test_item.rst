**git** test item
============================================================

The ``git`` test item records the state of one or more git repositories.
It has the following description format

.. code-block:: yaml
    :caption: ``git`` test item usage example

    - git:
        name: git test item
        repo: [$(test_directory), "/path_to/another/repo"]

Attributes
-----------------

* ``repo``: a path, or list of paths, to the root of the git repository or repositories to track.