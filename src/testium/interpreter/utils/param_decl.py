"""Declarative description of a test item's accepted parameters.

Each ``TestItem`` subclass declares its parameter surface as a class
attribute::

    class TestItemFoo(TestItem):
        PARAMS = ParamSet(
            Param("bar",      required=True,  doc="The bar value."),
            Param("baz",      default=0,      doc="Optional baz."),
            Param("modes",    kind=LIST,      doc="Iterable of modes."),
            Param("strategy", kind=ENUM("a", "b"), doc="..."),
            Param("opts",     kind=BLOCK,     doc="Sub-block."),
        )

The base ``TestItem.__init__`` consumes both ``COMMON_PARAMS`` (defined
in ``test_item.py``) and the subclass ``PARAMS`` to:

* warn on any key in the user's YAML that isn't declared anywhere
  (catches typos like ``param_filee``);
* expose a machine-readable schema for documentation generation and,
  eventually, an LSP server.

The descriptor is **purely about shape and naming**. Type coercion and
runtime checking of expanded values remain the responsibility of each
item's ``execute()`` method — most parameters are expressions
(``$(...)`` / ``<| ... |>``) whose effective type is only known after
expansion, so a static type would be misleading.

Validation of *values* (e.g. ``start_time`` must match HH:MM) can be
attached per-param via ``validate=lambda v: ...`` and is applied at
execution time on the expanded value, not at load time.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union


# ---------- Parameter "kinds" -------------------------------------------------
#
# These describe the YAML *shape* expected for a parameter, not its
# semantic type. They drive the LSP completion (do we suggest a single
# value, a list, a sub-block, an enum picker?) and the unknown-param
# diagnostic; nothing more.

SCALAR = "scalar"  # single value (string, number, bool, expression, ...)
LIST = "list"      # YAML list — the historical ``getParamAll`` case
BLOCK = "block"    # nested dict — e.g. ``cycle.exit:``


@dataclass(frozen=True)
class Enum:
    """Closed enumeration of acceptable scalar values."""
    values: tuple

    def __init__(self, *values):
        # frozen=True forbids assignment; bypass via object.__setattr__.
        object.__setattr__(self, "values", tuple(values))

    def __repr__(self):
        return f"Enum({', '.join(repr(v) for v in self.values)})"


Kind = Union[str, Enum]


# ---------- The descriptor ----------------------------------------------------

_MISSING = object()


@dataclass(frozen=True)
class Param:
    """Declarative description of one accepted parameter.

    Attributes
    ----------
    name : str
        The YAML key.
    kind : ``SCALAR`` (default) | ``LIST`` | ``BLOCK`` | ``Enum(...)``
        The YAML shape expected.
    required : bool
        If True, missing the parameter is a load-time error.
    default : Any
        Default value when the parameter is absent. ``_MISSING`` when no
        default was set (used to distinguish "absent" from "None").
    doc : str
        Free-form description used for hover / generated documentation.
    validate : Optional[Callable[[Any], bool]]
        Optional post-expansion validator, evaluated at ``execute()``
        time on the effective (expanded) value. Returning ``False``
        raises a clear error pointing at the param.
    """
    name: str
    kind: Kind = SCALAR
    required: bool = False
    default: Any = _MISSING
    doc: str = ""
    validate: Optional[Callable[[Any], bool]] = None

    def has_default(self):
        return self.default is not _MISSING

    def to_schema(self):
        """Return a dict suitable for JSON Schema generation."""
        s = {"name": self.name, "required": self.required, "doc": self.doc}
        if isinstance(self.kind, Enum):
            s["kind"] = "enum"
            s["enum"] = list(self.kind.values)
        else:
            s["kind"] = self.kind
        if self.has_default():
            s["default"] = self.default
        return s


class ParamSet:
    """Ordered, name-indexed collection of ``Param`` descriptors.

    Supports concatenation (``COMMON_PARAMS + SUBCLASS_PARAMS``) to
    merge the common surface with each item's own params. Later
    declarations override earlier ones (so a subclass can tighten a
    common param's docstring without redeclaring everything).
    """

    def __init__(self, *params):
        self._params = {}
        for p in params:
            self.add(p)

    def add(self, param):
        if not isinstance(param, Param):
            raise TypeError(f"ParamSet only accepts Param instances, got {type(param).__name__}")
        self._params[param.name] = param

    def __iter__(self):
        return iter(self._params.values())

    def __contains__(self, name):
        return name in self._params

    def __getitem__(self, name):
        return self._params[name]

    def names(self):
        return tuple(self._params.keys())

    def __add__(self, other):
        if not isinstance(other, ParamSet):
            return NotImplemented
        merged = ParamSet()
        merged._params = {**self._params, **other._params}
        return merged

    def to_schema(self):
        return [p.to_schema() for p in self._params.values()]


# ---------- Validation primitives --------------------------------------------

def unknown_keys(declared, user_dict):
    """Return the user-provided keys that are not declared in *declared*.

    *declared* is a ``ParamSet``; *user_dict* is the raw YAML mapping
    for the item. Unknown keys catch typos and obsolete parameters.
    """
    if not isinstance(user_dict, dict):
        return ()
    return tuple(k for k in user_dict.keys() if k not in declared)


def missing_required(declared, user_dict):
    """Return the names of declared required params absent from *user_dict*."""
    if not isinstance(user_dict, dict):
        return tuple(p.name for p in declared if p.required)
    return tuple(p.name for p in declared if p.required and p.name not in user_dict)
