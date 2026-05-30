
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

.. _sec_language_server:

Language server (editor support)
--------------------------------

*testium* ships a `Language Server Protocol
<https://microsoft.github.io/language-server-protocol/>`_ server so that
``.tum`` files get editor assistance — completion of test item types, hover
documentation of their parameters, and an outline view — in any LSP-capable
editor.

The server speaks LSP over standard input/output and is started with:

.. code-block:: text
    :caption: start the language server

    testium lsp

It is not meant to be launched directly by the user: an editor's LSP client
spawns it and drives the exchange. A VSCode / VSCodium client extension,
*testium_assist*, is provided for that purpose; any other LSP client (Neovim,
Emacs ``lsp-mode``, …) can be pointed at ``testium lsp`` as well.

The information the server exposes is the test item schema, which can also be
dumped as JSON for inspection or tooling:

.. code-block:: text
    :caption: dump the item / parameter schema

    testium schema

Because the schema is built from *testium* itself, every new item type or
parameter becomes available in the editor on the next *testium* upgrade, with
no change to the client.

The language server is included in the pre-built binary, Flatpak and AppImage
releases. For a source or wheel installation, pull the optional ``lsp``
dependencies:

.. code-block:: text
    :caption: enable the language server for a wheel / source install

    pip install 'testium[lsp]'
