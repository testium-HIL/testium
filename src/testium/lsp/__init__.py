"""testium language tooling.

Hosts the JSON-Schema-style schema export of every test item type, and a
``pygls`` language server that consumes the same schema to provide
completion / hover / diagnostics for ``.tum`` files in any LSP-capable
editor (VSCode, neovim, Helix, Emacs, …).

Entry points (both surfaced through the ``testium`` CLI):

- ``testium schema`` — dump the schema of every item type as JSON on stdout.
  Zero runtime dependencies; can be used by editors that already speak the
  YAML JSON Schema extension to get static completion immediately.

- ``testium lsp`` — start the language server over stdio. Requires the
  ``pygls`` optional dependency (``pip install testium[lsp]``).
"""
