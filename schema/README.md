# testium `.tum` JSON Schema

`tum.json` is the JSON Schema (draft 2020-12) describing valid `.tum`
test files. It is the committed output of `testium schema`, kept in sync
by the validation suite (`test/validation/schema_check.py`).

Intended consumers: yaml-language-server (`yaml.schemas`), external
linters (ajv, check-jsonschema) and AI assistants — anything that needs
the schema without running testium. The live equivalent is the
`testium schema` command.
