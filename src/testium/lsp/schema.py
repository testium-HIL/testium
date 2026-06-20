"""Schema export of the test item registry.

Walks every ``TestItemType`` entry (``interpreter/utils/constants.py``),
combines its declared ``PARAMS`` with the common ones, and returns a
serialisable structure keyed by ``item_cmd`` — the YAML key the user
writes (e.g. ``sleep``, ``py_func``, ``dialog_message``).

Items intentionally without ``PARAMS`` (the unstructured-body classes
like console ``write``/``writeln`` or plot ``add``/``export``) are
emitted as ``"params_declared": false`` so consumers know to suggest
nothing for them rather than reporting a closed empty set.

Action items (children of ``parallel``, ``console``, ``json_rpc``,
``plot``) are registered separately under each parent's ``actions``
entry — they're not top-level YAML keys, they live nested inside a
parent's ``steps:``.
"""

import json

from interpreter.utils.constants import TestItemType
from interpreter.utils.test_init import _constants_init


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


def _params_to_schema(item_class, common_params):
    """Return the params-portion of an item's schema entry.

    Common params are flagged so consumers can render them differently
    (an editor might show "common" parameters in a separate group).
    """
    own = getattr(item_class, "PARAMS", None)
    if own is None:
        return {"params_declared": False}
    common_names = set(common_params.names())
    params = []
    for p in common_params:
        d = p.to_schema()
        d["common"] = True
        params.append(d)
    for p in own:
        if p.name in common_names:
            # Subclass overrode a common param (e.g. tightened doc).
            for d in params:
                if d["name"] == p.name:
                    d.update(p.to_schema())
                    break
            continue
        d = p.to_schema()
        d["common"] = False
        params.append(d)
    return {"params_declared": True, "params": params}


def dump_all_schemas():
    """Return the full schema as a Python dict ready for json.dumps.

    Shape:
        {
          "items": {
            "sleep": {
              "display_name": "Sleep",
              "params_declared": true,
              "params": [{name, kind, required, default?, doc, common}, ...],
            },
            "console": {
              ...,
              "actions": {"open": {...}, "close": {...}, ...},
            },
            ...
          }
        }
    """
    _constants_init()
    # Imported lazily — pulls test_item.py which references constants.
    from interpreter.test_items.test_item import COMMON_PARAMS

    out = {"items": {}}
    for tp in TestItemType:
        cls = getattr(tp, "item_class", None)
        if cls is None:
            continue
        # Action types (CONSOLE_ACTION, GRAPH_ACTION, JSON_RPC_ACTION) have no
        # standalone YAML representation — skip them here, they show up under
        # their parent's "actions" key.
        cmd = tp.item_cmd
        if cmd.endswith("_action"):
            continue
        entry = {"display_name": tp.item_name}
        entry.update(_params_to_schema(cls, COMMON_PARAMS))

        actions = _collect_action_classes(cls)
        if actions:
            entry["actions"] = {
                name: _params_to_schema(acls, COMMON_PARAMS)
                for name, acls in actions.items()
            }
            for name in entry["actions"]:
                entry["actions"][name]["display_name"] = name

        out["items"][cmd] = entry
    return out


def dump_all_schemas_json(indent=2):
    """Same as ``dump_all_schemas`` but serialised to a JSON string."""
    return json.dumps(dump_all_schemas(), indent=indent, sort_keys=False,
                      default=str)
