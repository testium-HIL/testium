"""JSON Schema export of the test item registry.

``dump_jsonschema()`` produces a JSON Schema (draft 2020-12) describing
every valid ``.tum`` file. Derived from each item's declarative
``PARAMS = ParamSet(...)`` and ``ACTIONS = {key: cls}`` class
attributes (see ``interpreter/utils/param_decl.py``). Consumed by:

- the LSP server (``testium lsp``) for completion / hover;
- the ``testium schema`` CLI dump;
- external validators (yaml-language-server, ajv, check-jsonschema);
- AI agents that need a formal description of ``.tum``.
"""

import json

from interpreter.utils.constants import TestItemType
from interpreter.utils.test_init import _constants_init
from interpreter.utils.param_decl import LIST, BLOCK, Enum
from interpreter.utils.version import get_testium_release_version


# Action class -> parent cmd (the action's parent in the YAML). Action classes
# aren't first-class TestItemType entries (TYPE_*_ACTION is one generic bucket),
# so we resolve their YAML key from the parent's declarative ``ACTIONS`` map.
def _collect_action_classes(parent_class):
    """Return {action_yaml_key: action_class} for a TestItemActions parent.

    Each parent declares its actions as a class-level ``ACTIONS = {key: class}``
    attribute (see ``item_actions/TestItemActions``). We read it directly — no
    instantiation, no source inspection — so this works identically whether the
    package runs from source, a wheel, or a frozen (PyInstaller) build where the
    ``.py`` source isn't on disk.
    """
    return dict(getattr(parent_class, "ACTIONS", None) or {})


# JSON Schema id; opaque URN (no fetch required, see DESIGN.md schema notes).
_JSONSCHEMA_ID_PREFIX = "urn:testium:tum-schema:"


def _common_param_names(common_params):
    return set(common_params.names())


def _item_def_jsonschema(item_class, display_name, common_params, defs,
                         def_prefix):
    """Return the JSON Schema fragment describing one item / action.

    *defs* is the running ``$defs`` map: nested actions register their
    own ``$def`` into it as a side-effect. ``def_prefix`` namespaces
    the nested defs (e.g. ``console_open`` rather than just ``open``).
    """
    own = getattr(item_class, "PARAMS", None)
    if own is None:
        # Unstructured-body items (console write/writeln, plot add/export):
        # the YAML value is the raw payload, not a mapping. Accept any scalar
        # or list (plot add takes a list of points).
        return {
            "description": display_name,
        }

    common_names = _common_param_names(common_params)
    properties = {}
    required = []

    for p in common_params:
        properties[p.name] = p.to_jsonschema()
    for p in own:
        properties[p.name] = p.to_jsonschema()
        if p.required:
            required.append(p.name)
    # If a common param is marked required by the subclass override, surface it.
    for p in common_params:
        if p.required and p.name not in required:
            required.append(p.name)

    actions = _collect_action_classes(item_class)
    if actions:
        # Override the generic ``steps`` (inherited from common) with the
        # strict action-list shape: each step is a mapping with exactly one
        # action key drawn from this parent's ACTIONS.
        action_props = {}
        for action_name, action_cls in actions.items():
            sub_def = f"{def_prefix}_{action_name}"
            defs[sub_def] = _item_def_jsonschema(
                action_cls, action_name, common_params, defs, sub_def,
            )
            action_props[action_name] = {"$ref": f"#/$defs/{sub_def}"}
        properties["steps"] = {
            "type": "array",
            "items": {
                "type": "object",
                "minProperties": 1,
                "maxProperties": 1,
                "additionalProperties": False,
                "properties": action_props,
            },
        }

    schema = {
        "type": "object",
        "description": display_name,
        "additionalProperties": False,
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema


def dump_jsonschema():
    """Return a JSON Schema (draft 2020-12) describing valid ``.tum`` files.

    Shape:
        - root object accepting ``config_file`` (array of strings) and
          ``main`` (an item, required);
        - one ``$def`` per item type (``sleep``, ``py_func``, ``console``…)
          and one per nested action (``console_open``, ``json_rpc_query``…);
        - the ``steps`` array of action parents (console / plot / json_rpc)
          is strictly constrained to that parent's actions.

    Permissive on individual values: most parameters carry testium
    expressions (``$(...)`` / ``<| ... |>``) so a strict literal type
    would be misleading. ``Param.type`` is honoured when set.
    """
    _constants_init()
    from interpreter.test_items.test_item import COMMON_PARAMS

    defs = {}

    # Per-item $defs and a steps-item shape listing top-level items.
    step_alternatives = {}
    for tp in TestItemType:
        cls = getattr(tp, "item_class", None)
        if cls is None:
            continue
        cmd = tp.item_cmd
        if cmd == "default":
            # Root sentinel: structurally identical to a generic item; we
            # emit `_main` separately below.
            continue
        if cmd.endswith("_action"):
            continue
        defs[cmd] = _item_def_jsonschema(
            cls, tp.item_name, COMMON_PARAMS, defs, cmd,
        )
        step_alternatives[cmd] = {"$ref": f"#/$defs/{cmd}"}

    # Generic step element: a single-key mapping picking one top-level item.
    defs["_step"] = {
        "type": "object",
        "minProperties": 1,
        "maxProperties": 1,
        "additionalProperties": False,
        "properties": step_alternatives,
    }
    defs["_steps"] = {
        "type": "array",
        "items": {"$ref": "#/$defs/_step"},
    }

    # Root `main` item: identical surface to other items, but its `steps`
    # contains top-level items (not actions). We re-emit it explicitly with
    # the strict array shape.
    main_props = {p.name: p.to_jsonschema() for p in COMMON_PARAMS}
    main_props["steps"] = {"$ref": "#/$defs/_steps"}
    defs["_main"] = {
        "type": "object",
        "description": "Top-level test container",
        "additionalProperties": False,
        "required": ["steps"],
        "properties": main_props,
    }

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": _JSONSCHEMA_ID_PREFIX + get_testium_release_version(),
        "title": "testium TUM file",
        "type": "object",
        "additionalProperties": False,
        "required": ["main"],
        "properties": {
            "config_file": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of YAML config files to load.",
            },
            "main": {"$ref": "#/$defs/_main"},
            "report": {
                "type": "object",
                "description": "Top-level report configuration (enabled,"
                               " log_stored, export, …).",
            },
        },
        "$defs": defs,
    }


def dump_jsonschema_json(indent=2):
    """Serialise :func:`dump_jsonschema` to a JSON string."""
    return json.dumps(dump_jsonschema(), indent=indent, sort_keys=False,
                      default=str)
