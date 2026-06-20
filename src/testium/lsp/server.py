"""LSP server for ``.tum`` files.

Features available so far:

- **Completion** — when the user starts a new YAML step (``- <cursor>``),
  the server proposes the full list of known item types. The completion
  item carries a short hover-style description listing required and
  optional parameters.
- **Hover** — over a known item-type word (``sleep``, ``py_func``, …)
  the server renders the same description in a popup.
- **Document symbols (outline)** — every ``- <type>:`` line becomes an
  entry in the editor's outline view. Nesting follows YAML indentation,
  so containers (``group``, ``loop``, ``parallel``, ``console`` …)
  display their children as a subtree.

The server speaks LSP over stdio. Start it with::

    testium lsp

Editors invoke it through their LSP client; the connection layer
(``vscode-languageclient``, ``nvim-lspconfig``, ``lsp-mode``, …) takes
care of the JSON-RPC framing.

Architecture notes
------------------

The schema is built once at server start (``dump_jsonschema()``) and
kept in memory; an editor restart picks up upstream changes. The schema
is the **only** source of truth — when testium adds a new item type or
parameter, the LSP automatically exposes it without any change here.

The current handlers stay deliberately heuristic on the parser side:
completion uses a line-prefix regex, outline a per-line ``- <known>:``
sweep with indentation tracking. A proper YAML+Jinja parsing pass is
still pending and is the prerequisite for *parameter*-level completion
and diagnostics.
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
        TEXT_DOCUMENT_DOCUMENT_SYMBOL,
        TEXT_DOCUMENT_HOVER,
        CompletionItem,
        CompletionItemKind,
        CompletionList,
        CompletionOptions,
        CompletionParams,
        DocumentSymbol,
        DocumentSymbolParams,
        Hover,
        HoverParams,
        InsertTextFormat,
        MarkupContent,
        MarkupKind,
        Position,
        Range,
        SymbolKind,
    )
except ImportError as exc:
    # Surfaced by the CLI dispatcher with a friendly install hint.
    raise


from lsp.schema import dump_jsonschema


_LINE_START_STEP = re.compile(r"^\s*-\s*([A-Za-z_][A-Za-z0-9_]*)?\s*:?\s*$")

# Matches "- <identifier>:" for outline / hover purposes. Captures the start
# column of the identifier and the identifier itself. Trailing tokens after
# the colon (inline-form params, comments) are tolerated.
_STEP_LINE = re.compile(r"^(?P<lead>\s*-\s*)(?P<ident>[A-Za-z_][A-Za-z0-9_]*)\s*:")

# Matches a ``name: <value>`` line under an item — used by the outline pass
# to surface the user's display name next to the item type.
_NAME_FIELD = re.compile(r"^\s*name\s*:\s*(?P<value>.+?)\s*$")

# Word boundary used by hover to extract the identifier under the cursor.
_IDENT_AT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _common_param_names():
    """Return the set of parameter names shared by every test item."""
    from interpreter.test_items.test_item import COMMON_PARAMS
    return set(COMMON_PARAMS.names())


def _walk_schema(schema):
    """Index the JSON Schema for LSP consumption.

    Returns ``(top_level, actions)``:

    - ``top_level`` maps every item ``$def`` name (``sleep``, ``console``,
      ``py_func`` …) to its entry.
    - ``actions`` maps an action's YAML key (``open``, ``read_until``,
      ``add`` …) to the first action entry encountered for it. Action
      entries reachable as ``$ref`` (``console_open`` …) are pruned from
      ``top_level``.

    Detection relies on the schema structure rather than a hardcoded
    parent list: an entry whose ``properties.steps.items`` is a
    ``additionalProperties: false`` mapping is treated as an action
    parent, and the keys of that mapping are its action names.
    """
    defs = schema.get("$defs", {})
    action_subdefs = set()
    actions = {}
    for cmd, entry in defs.items():
        if cmd.startswith("_"):
            continue
        steps_items = ((entry.get("properties") or {})
                       .get("steps") or {}).get("items") or {}
        if steps_items.get("additionalProperties") is not False:
            continue
        for action_name, val in (steps_items.get("properties") or {}).items():
            ref = val.get("$ref", "") if isinstance(val, dict) else ""
            if ref.startswith("#/$defs/"):
                sub = ref[len("#/$defs/"):]
                action_subdefs.add(sub)
                actions.setdefault(action_name, defs.get(sub, {}))
            else:
                actions.setdefault(action_name, val if isinstance(val, dict) else {})
    top_level = {
        cmd: entry for cmd, entry in defs.items()
        if not cmd.startswith("_") and cmd not in action_subdefs
    }
    return top_level, actions


def _render_item_markdown(cmd, entry, common_names):
    """Render a schema entry as a Markdown hover string.

    Reused by both the completion-item documentation and the hover
    handler so the editor presents identical information regardless of
    how the user reached it.

    Common parameters (``name``, ``doc``, ``stop_on_failure`` …) are
    filtered out so only the item-specific surface is listed.
    """
    detail = entry.get("description", cmd)
    lines = [f"**{cmd}** — {detail}", ""]
    properties = entry.get("properties")
    if not properties:
        lines.append("(Parameter list is not described — this item's body is the "
                     "raw user value.)")
        return "\n".join(lines)
    required = set(entry.get("required", []))
    own = [name for name in properties if name not in common_names]
    req = [n for n in own if n in required]
    opt = [n for n in own if n not in required]
    if req:
        lines.append("Required parameters:")
        for n in req:
            doc = properties[n].get("description", "")
            lines.append(f"- `{n}` — {doc}")
        lines.append("")
    if opt:
        lines.append("Optional parameters:")
        for n in opt:
            doc = properties[n].get("description", "")
            lines.append(f"- `{n}` — {doc}")
    return "\n".join(lines)


def _build_item_completions(top_level, common_names):
    """Return a list of CompletionItem covering every top-level item type.

    Each completion inserts ``<name>:`` with the cursor positioned after
    the colon so the user can immediately start typing parameters.
    """
    items = []
    for cmd, entry in top_level.items():
        items.append(
            CompletionItem(
                label=cmd,
                kind=CompletionItemKind.Class,
                detail=entry.get("description", cmd),
                documentation=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=_render_item_markdown(cmd, entry, common_names),
                ),
                insert_text=f"{cmd}:",
                insert_text_format=InsertTextFormat.PlainText,
            )
        )
    items.sort(key=lambda it: it.label)
    return items


def _word_at(line, character):
    """Return ``(start, end, text)`` of the identifier under ``character``.

    Returns ``None`` when the cursor isn't on a word. Used by hover.
    """
    for m in _IDENT_AT.finditer(line):
        if m.start() <= character <= m.end():
            return m.start(), m.end(), m.group(0)
    return None


def _build_document_symbols(lines, item_cmds):
    """Walk ``lines`` and produce a nested ``DocumentSymbol`` tree.

    Heuristics (no YAML parsing yet):
    - Each ``- <known_cmd>:`` line becomes a symbol.
    - Nesting follows the indentation of the leading ``-``: a deeper-
      indented step is treated as a child of the most recent shallower
      step.
    - The symbol's ``detail`` is the ``name: <value>`` field if found
      within a small window after the step header (no YAML parsing —
      we just look at indented lines that aren't another ``- …`` step).

    The result is suitable for the LSP outline panel even when the
    surrounding YAML is mid-edit and structurally invalid.
    """
    root_children = []
    # Each stack entry: (indent_col, children_list_to_append_to,
    #                    pending_parent_symbol or None).
    stack = [(-1, root_children, None)]

    def _attach_name(parent_symbol, start_line):
        """Look for the nearest ``name:`` field in the children of ``parent``."""
        if parent_symbol is None or start_line + 1 >= len(lines):
            return
        base_indent = len(lines[start_line]) - len(lines[start_line].lstrip(" "))
        for j in range(start_line + 1, min(start_line + 10, len(lines))):
            l = lines[j]
            stripped = l.lstrip(" ")
            indent = len(l) - len(stripped)
            if indent <= base_indent and stripped.strip() != "":
                break
            m = _NAME_FIELD.match(l)
            if m:
                value = m.group("value").strip("\"' ")
                parent_symbol.detail = value
                return

    for i, raw_line in enumerate(lines):
        m = _STEP_LINE.match(raw_line)
        if not m:
            continue
        cmd = m.group("ident")
        if cmd not in item_cmds:
            continue
        indent = len(m.group("lead")) - len(m.group("lead").lstrip(" "))
        # Pop the stack until we find a parent with strictly smaller indent.
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            stack.append((-1, root_children, None))
        parent_children = stack[-1][1]

        ident_start = m.start("ident")
        ident_end = m.end("ident")
        symbol = DocumentSymbol(
            name=cmd,
            detail=None,
            kind=SymbolKind.Function,
            range=Range(
                start=Position(line=i, character=0),
                end=Position(line=i, character=len(raw_line.rstrip("\n"))),
            ),
            selection_range=Range(
                start=Position(line=i, character=ident_start),
                end=Position(line=i, character=ident_end),
            ),
            children=[],
        )
        parent_children.append(symbol)
        stack.append((indent, symbol.children, symbol))
        _attach_name(symbol, i)
    return root_children


def _make_server():
    server = LanguageServer("testium-lsp", "0.1.0")
    schema = dump_jsonschema()
    common_names = _common_param_names()
    top_level, actions = _walk_schema(schema)
    item_completions = _build_item_completions(top_level, common_names)
    # Known YAML keys accepted by outline / hover: top-level items plus
    # nested action names (open, close, write, read_until, add …).
    item_cmds = set(top_level) | set(actions)

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

    @server.feature(TEXT_DOCUMENT_HOVER)
    def hover(params: HoverParams):
        doc = server.workspace.get_text_document(params.text_document.uri)
        line_idx = params.position.line
        if line_idx >= len(doc.lines):
            return None
        line = doc.lines[line_idx]
        # Only respond when the cursor is on the type part of a step line
        # ("- sleep:") — never for arbitrary words in a string.
        step_match = _STEP_LINE.match(line)
        if not step_match:
            return None
        word = _word_at(line, params.position.character)
        if word is None:
            return None
        start, end, text = word
        if text != step_match.group("ident") or text not in item_cmds:
            return None
        entry = top_level.get(text) or actions.get(text)
        if entry is None:
            return None
        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=_render_item_markdown(text, entry, common_names),
            ),
            range=Range(
                start=Position(line=line_idx, character=start),
                end=Position(line=line_idx, character=end),
            ),
        )

    @server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def document_symbols(params: DocumentSymbolParams):
        doc = server.workspace.get_text_document(params.text_document.uri)
        return _build_document_symbols(doc.lines, item_cmds)

    return server


def serve():
    """Start the LSP server on stdio. Blocks until the client disconnects."""
    server = _make_server()
    server.start_io()
