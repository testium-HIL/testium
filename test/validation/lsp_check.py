#!/usr/bin/env python3
"""Per-channel check of the testium language server.

Given the channel's testium invocation as argv (e.g. ``flatpak run
--command=testium org.testium.Testium``, a PyInstaller binary path, or
``python -m testium``), verify two things end-to-end against that exact build:

  1. ``<cmd> schema`` produces a valid JSON Schema (draft 2020-12) whose
     ``$defs`` still include the nested action sets
     (``console_open``, ``plot_add``, ``json_rpc_query``…). This catches
     a frozen build that lost the declarative ``ACTIONS`` registry.
  2. ``<cmd> lsp`` starts a real language server: it must answer an LSP
     ``initialize`` request with a capabilities result and must NOT report the
     pygls dependency as missing. This catches a channel that forgot to bundle
     the ``[lsp]`` extra.

Exits non-zero (with a diagnostic) on the first failure so the validation run
fails loudly. Used by ``run.sh`` before launching the main suite.
"""
import json
import subprocess
import sys

EXPECTED_ACTIONS = {
    "console": ("open", "close", "write", "writeln", "read_until"),
    "plot": ("open", "close", "add", "export"),
    "json_rpc": ("open", "close", "query", "receive"),
}


def fail(msg):
    print(f"LSP CHECK: FAIL — {msg}", file=sys.stderr)
    sys.exit(1)


def _extract_json(raw):
    """Parse JSON from ``raw`` bytes, tolerating leading non-JSON noise.

    The source-mode launcher (run.sh) may print env-setup lines before the
    schema JSON, so we fall back to parsing from the first ``{``.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find(b"{")
        if start < 0:
            raise
        return json.loads(raw[start:])


def check_schema(cmd):
    try:
        out = subprocess.run(cmd + ["schema"], capture_output=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        fail(f"`{' '.join(cmd)} schema` could not run: {e}")
    if out.returncode != 0:
        fail(f"`schema` exited {out.returncode}: {out.stderr.decode()[:300]}")
    try:
        data = _extract_json(out.stdout)
    except json.JSONDecodeError as e:
        fail(f"`schema` output is not valid JSON: {e}")
    defs = data.get("$defs", {})
    if not defs:
        fail(f"schema has no $defs — output is not a JSON Schema dump")
    for parent, actions in EXPECTED_ACTIONS.items():
        missing = [a for a in actions if f"{parent}_{a}" not in defs]
        if missing:
            fail(f"schema $defs missing actions for '{parent}': {missing} — a "
                 f"frozen build lost the declarative ACTIONS (def keys: "
                 f"{sorted(defs)[:8]}…)")
    action_defs = {
        f"{parent}_{action}"
        for parent, actions in EXPECTED_ACTIONS.items() for action in actions
    }
    item_defs = [k for k in defs
                 if not k.startswith("_") and k not in action_defs]
    print(f"LSP CHECK: schema OK ({len(item_defs)} items; actions present for "
          f"{', '.join(EXPECTED_ACTIONS)})")


def _frame(msg):
    body = json.dumps(msg).encode()
    return b"Content-Length: %d\r\n\r\n%s" % (len(body), body)


def _parse_frames(data):
    pos = 0
    while pos < len(data):
        end_headers = data.find(b"\r\n\r\n", pos)
        if end_headers < 0:
            return
        headers = data[pos:end_headers].decode("latin-1")
        body_start = end_headers + 4
        content_length = None
        for line in headers.split("\r\n"):
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())
        if content_length is None:
            return
        body_end = body_start + content_length
        if body_end > len(data):
            return
        try:
            yield json.loads(data[body_start:body_end])
        except json.JSONDecodeError:
            return
        pos = body_end


def check_lsp(cmd):
    # Single-document session: line 0 is "- sleep:" (target for hover on the
    # 'sleep' identifier), line 1 is "- " (target for completion after the
    # dash so the start-of-step regex matches).
    doc_uri = "file:///tmp/testium-lsp-check.tum"
    doc_text = "- sleep:\n- "
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"processId": None, "rootUri": None, "capabilities": {}}},
        {"jsonrpc": "2.0", "method": "initialized", "params": {}},
        {"jsonrpc": "2.0", "method": "textDocument/didOpen",
         "params": {"textDocument": {
             "uri": doc_uri, "languageId": "yaml",
             "version": 1, "text": doc_text}}},
        {"jsonrpc": "2.0", "id": 2, "method": "textDocument/completion",
         "params": {"textDocument": {"uri": doc_uri},
                    "position": {"line": 1, "character": 2}}},
        {"jsonrpc": "2.0", "id": 3, "method": "textDocument/hover",
         "params": {"textDocument": {"uri": doc_uri},
                    "position": {"line": 0, "character": 4}}},
        {"jsonrpc": "2.0", "id": 4, "method": "shutdown"},
        {"jsonrpc": "2.0", "method": "exit"},
    ]
    payload = b"".join(_frame(m) for m in messages)
    try:
        out = subprocess.run(cmd + ["lsp"], input=payload,
                             capture_output=True, timeout=30)
        stdout, stderr = out.stdout, out.stderr
    except subprocess.TimeoutExpired as e:
        stdout, stderr = e.stdout or b"", e.stderr or b""

    if b"dependencies missing" in stdout + stderr:
        fail("`lsp` reports the pygls dependency missing — this channel did "
             "not bundle the [lsp] extra.")

    responses = {f.get("id"): f for f in _parse_frames(stdout) if "id" in f}
    init = responses.get(1)
    if not init or "capabilities" not in (init.get("result") or {}):
        fail(f"`lsp` did not return initialize capabilities. "
             f"stdout[:200]={stdout[:200]!r} stderr[:200]={stderr[:200]!r}")
    print("LSP CHECK: lsp initialize OK (server answered with capabilities)")

    comp = responses.get(2)
    items = (comp or {}).get("result")
    if isinstance(items, dict):
        items = items.get("items")
    if not items:
        fail(f"`lsp` returned no completion items at '- |' position. "
             f"response={comp!r}")
    labels = {it.get("label") for it in items}
    expected = {"sleep", "let", "console", "py_func", "group"}
    missing = expected - labels
    if missing:
        fail(f"`lsp` completion is missing expected items: {sorted(missing)} "
             f"(got {len(labels)} labels)")
    print(f"LSP CHECK: lsp completion OK ({len(labels)} item types proposed)")

    hov = responses.get(3)
    hover_text = ((hov or {}).get("result") or {}).get("contents")
    if isinstance(hover_text, dict):
        hover_text = hover_text.get("value", "")
    elif not isinstance(hover_text, str):
        hover_text = ""
    if "sleep" not in hover_text.lower():
        fail(f"`lsp` hover on 'sleep' did not return relevant content. "
             f"response={hov!r}")
    print("LSP CHECK: lsp hover OK (sleep description returned)")


def main():
    cmd = sys.argv[1:]
    if not cmd:
        fail("usage: lsp_check.py <testium-invocation...>")
    check_schema(cmd)
    check_lsp(cmd)
    print("LSP CHECK: PASS")


if __name__ == "__main__":
    main()
