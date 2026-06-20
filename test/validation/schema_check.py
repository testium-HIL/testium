#!/usr/bin/env python3
"""Per-channel check of the testium JSON Schema.

Given the channel's testium invocation as argv (e.g.
``flatpak run --command=testium org.testium.Testium``, the PyInstaller
binary, or ``./run.sh``), verify three things end-to-end:

  1. ``<cmd> schema`` produces a syntactically valid JSON Schema
     (meta-validation against draft 2020-12).
  2. The versioned ``schema/tum.json`` in the repo matches the live
     output of ``<cmd> schema``. Drift means someone forgot to
     regenerate the file after touching ``PARAMS``/``ACTIONS``.
  3. Each ``.tum`` template under ``schema/test_schema/`` validates
     against the schema. These are the positive fixtures shipped with
     the repo to exercise every item type.

Exits non-zero with a diagnostic on the first failure so the validation
run fails loudly.
"""
import json
import os
import subprocess
import sys

import yaml
import jsonschema


def fail(msg):
    print(f"SCHEMA CHECK: FAIL - {msg}", file=sys.stderr)
    sys.exit(1)


def _extract_json(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find(b"{")
        if start < 0:
            raise
        return json.loads(raw[start:])


def main():
    cmd = sys.argv[1:]
    if not cmd:
        fail("usage: schema_check.py <testium-invocation...>")

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    schema_dir = os.path.join(repo_root, "schema")
    versioned_path = os.path.join(schema_dir, "tum.json")
    fixtures_dir = os.path.join(schema_dir, "test_schema")

    # 1. testium schema output is valid JSON Schema.
    try:
        out = subprocess.run(cmd + ["schema"], capture_output=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        fail(f"`{' '.join(cmd)} schema` could not run: {e}")
    if out.returncode != 0:
        fail(f"`schema` exited {out.returncode}: {out.stderr.decode()[:300]}")
    try:
        live = _extract_json(out.stdout)
    except json.JSONDecodeError as e:
        fail(f"`schema` output is not valid JSON: {e}")
    try:
        jsonschema.Draft202012Validator.check_schema(live)
    except jsonschema.SchemaError as e:
        fail(f"`schema` output is not a valid JSON Schema: {e.message}")
    print("SCHEMA CHECK: live schema is valid draft 2020-12")

    # 2. Versioned file matches the live output.
    if not os.path.isfile(versioned_path):
        fail(f"missing versioned schema at {versioned_path}")
    with open(versioned_path) as f:
        versioned = json.load(f)
    if versioned != live:
        fail(f"versioned {versioned_path} is out of sync with `testium "
             f"schema` - regenerate with `testium schema > schema/tum.json`")
    print("SCHEMA CHECK: versioned schema matches live output")

    # 3. Each fixture .tum validates. schema/test.tum is the canonical
    # top-level example; schema/test_schema/*.tum exercise one item type each.
    validator = jsonschema.Draft202012Validator(live)
    fixtures = [("test.tum", schema_dir)]
    fixtures += [(f, fixtures_dir)
                 for f in sorted(os.listdir(fixtures_dir))
                 if f.endswith(".tum")]
    failures = []
    for name, base_dir in fixtures:
        path = os.path.join(base_dir, name)
        with open(path) as f:
            text = f.read()
        if "{%" in text or "{{" in text:
            print(f"SCHEMA CHECK: {name} SKIP (jinja)")
            continue
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            failures.append((name, f"YAML parse error: {e}"))
            continue
        errs = list(validator.iter_errors(data))
        if errs:
            failures.append((name,
                             ", ".join(e.message[:120] for e in errs[:2])))
        else:
            print(f"SCHEMA CHECK: {name} OK")

    if failures:
        for name, msg in failures:
            print(f"SCHEMA CHECK: {name} FAIL - {msg}", file=sys.stderr)
        fail(f"{len(failures)} fixture(s) failed schema validation")

    print(f"SCHEMA CHECK: PASS ({len(fixtures)} fixtures)")


if __name__ == "__main__":
    main()
