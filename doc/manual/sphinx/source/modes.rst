
Modes of operation
====================

.. _sec_graphical_mode:

Graphical mode
---------------

*testium* tool has been initially designed to have Graphical User's interface.

The way to call it is simply by executing the ``testium`` command. It is the normal mode.

.. _sec_batch_mode:

Batch mode
----------

The batch mode allows to execute a test in text mode. In this mode, the test does not start any
graphical interface.

.. code-block:: text
    :caption: call a test in batch mode

    testium -b test/my_test/main.tum
