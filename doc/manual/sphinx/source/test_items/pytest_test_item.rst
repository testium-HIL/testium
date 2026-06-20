**pytest** test item
============================================================

The ``pytest`` test item runs a `pytest <https://docs.pytest.org>`_ test
file and turns every collected test into a child item, each with its own
``PASS`` / ``FAIL`` / ``SKIP`` result, duration and failure message. It is the
pytest counterpart of the ``unittest`` test item.

The tum file prototype is as followed:

.. code-block:: yaml
    :caption: ``pytest`` test item usage example

    - pytest:
        name: pytest test item
        test_file: test_device.py
        test_method:
            - test_boot
            - test_version

Attributes
------------------

Beside common test items attributes, the pytest test item has specific
attributes:

* ``test_file``: the name (and eventually path) of the pytest file to run.
* ``test_method``: optional list of test function names. When present, only
  the matching tests are included in the test tree (the name is matched
  against the function part of each pytest *node id*, the parametrisation
  suffix being ignored). Otherwise every collected test in the file is run.

Host execution
------------------

Unlike ``unittest`` (which runs in *testium*'s own interpreter), the
``pytest`` item runs pytest in a **subprocess on the host interpreter** — the
same one used by ``py_func`` / ``lua_func`` (overridable with the
``python_bin`` global variable). As a consequence:

* ``pytest`` (and the test's own dependencies) must be installed on that host
  interpreter — e.g. ``pip install pytest``. It is not bundled with *testium*.
* the tests run isolated from *testium*'s in-process API; they are meant to be
  self-contained (they exercise the device/software under test, not the
  *testium* tree).

The item is invoked with a controlled pytest configuration
(``--capture=no``, user ``addopts`` neutralised, cache disabled); a small
built-in pytest plugin reports the collected tests and their results back to
*testium*.
