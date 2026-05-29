"""LSP server for ``.tum`` files (MVP).

This first iteration provides a single feature — completion of test item
type names at the start of a YAML step (``- <cursor>``). Hover, outline,
and diagnostics will be added in subsequent commits; they all share the
schema obtained from :mod:`testium.lsp.schema`.

The server speaks LSP over stdio. Start it with::

    testium lsp

Editors invoke it through their LSP client; the connection layer
(``vscode-languageclient``, ``nvim-lspconfig``, ``lsp-mode``, …) takes
care of the JSON-RPC framing.

Architecture notes
------------------

We build the schema once at server start. It is **not** reloaded when
the user upgrades testium because the server is meant to be restarted
in that case (editors typically restart the language server on a
package upgrade). The schema is a few KB of JSON-equivalent data so
keeping it in memory is trivial.

The completion handler is intentionally heuristic: we look at the
characters preceding the cursor on the current line. A line that
matches ``\\s*-\\s*$`` (optionally followed by an identifier prefix)
means the user is starting a new step — we offer the item types.
Anything else returns no completions for now; richer YAML-context
analysis comes with the diagnostic / hover passes.
"""

import re

try:
    # pygls 2.x moved LanguageServer under pygls.lsp.server. We pin >=1.3 in
    # the optional dependency to stay open to either family, but the import
    # path differs — try the new one first, then the legacy one.
    try:
        from pygls.lsp.server import LanguageServer
    except ImportError:
        from pygls.server import LanguageServer  # pygls < 2
    from lsprotocol.types import (
        TEXT_DOCUMENT_COMPLETION,
        CompletionItem,
        CompletionItemKind,
        CompletionList,
        CompletionOptions,
        CompletionParams,
        InsertTextFormat,
    )
except ImportError as exc:
    # Surfaced by the CLI dispatcher with a friendly install hint.
    raise


from lsp.schema import dump_all_schemas


_LINE_START_STEP = re.compile(r"^\s*-\s*([A-Za-z_][A-Za-z0-9_]*)?\s*:?\s*$")


def _build_item_completions(schema):
    """Return a list of CompletionItem covering every top-level item type.

    Each completion inserts ``<name>:`` with the cursor positioned after
    the colon so the user can immediately start typing parameters. The
    item's display name and the first non-common required param (if any)
    show up in the hover-style detail/documentation.
    """
    items = []
    for cmd, entry in schema["items"].items():
        if cmd == "default":
            # Root sentinel; never appears as a YAML key.
            continue
        detail = entry.get("display_name", cmd)
        doc_lines = [f"**{detail}**", ""]
        if entry.get("params_declared"):
            non_common = [p for p in entry["params"] if not p["common"]]
            required = [p for p in non_common if p["required"]]
            optional = [p for p in non_common if not p["required"]]
            if required:
                doc_lines.append("Required parameters:")
                for p in required:
                    doc_lines.append(f"- `{p['name']}` — {p['doc']}")
                doc_lines.append("")
            if optional:
                doc_lines.append("Optional parameters:")
                for p in optional:
                    doc_lines.append(f"- `{p['name']}` — {p['doc']}")
        items.append(
            CompletionItem(
                label=cmd,
                kind=CompletionItemKind.Class,
                detail=detail,
                documentation="\n".join(doc_lines),
                insert_text=f"{cmd}:",
                insert_text_format=InsertTextFormat.PlainText,
            )
        )
    items.sort(key=lambda it: it.label)
    return items


def _make_server():
    server = LanguageServer("testium-lsp", "0.1.0")
    schema = dump_all_schemas()
    item_completions = _build_item_completions(schema)

    @server.feature(
        TEXT_DOCUMENT_COMPLETION,
        CompletionOptions(trigger_characters=["-", " "]),
    )
    def completion(params: CompletionParams):
        doc = server.workspace.get_text_document(params.text_document.uri)
        line_idx = params.position.line
        if line_idx >= len(doc.lines):
            return CompletionList(is_incomplete=False, items=[])
        line = doc.lines[line_idx]
        # Only look at what's left of the cursor.
        prefix = line[: params.position.character]
        if not _LINE_START_STEP.match(prefix):
            return CompletionList(is_incomplete=False, items=[])
        return CompletionList(is_incomplete=False, items=item_completions)

    return server


def serve():
    """Start the LSP server on stdio. Blocks until the client disconnects."""
    server = _make_server()
    server.start_io()
