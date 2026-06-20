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


def check_lsp(cmd):
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"processId": None, "rootUri": None, "capabilities": {}},
    }).encode()
    msg = b"Content-Length: %d\r\n\r\n%s" % (len(body), body)
    try:
        out = subprocess.run(cmd + ["lsp"], input=msg,
                             capture_output=True, timeout=30)
        stdout, stderr = out.stdout, out.stderr
    except subprocess.TimeoutExpired as e:
        # A server that stays alive past initialize is fine — it just never saw
        # a shutdown. Use whatever it wrote so far as the response.
        stdout, stderr = e.stdout or b"", e.stderr or b""
    blob = stdout + stderr
    if b"dependencies missing" in blob:
        fail("`lsp` reports the pygls dependency missing — this channel did "
             "not bundle the [lsp] extra.")
    if b'"capabilities"' not in stdout:
        fail("`lsp` did not return an initialize result. "
             f"stdout[:200]={stdout[:200]!r} stderr[:200]={stderr[:200]!r}")
    print("LSP CHECK: lsp initialize OK (server answered with capabilities)")


def main():
    cmd = sys.argv[1:]
    if not cmd:
        fail("usage: lsp_check.py <testium-invocation...>")
    check_schema(cmd)
    check_lsp(cmd)
    print("LSP CHECK: PASS")


if __name__ == "__main__":
    main()
