import json
import threading
from threading import Lock


global_dict = {}

global_dict_lock = Lock()

_update_queue = None

# Read-side resolution: values are stored as declared; resolve_gd expands
# $()/<| |> on demand and memoizes until any write (generation counter).
_generation = 0
_resolver = None
_resolved_cache = {}
_cache_lock = Lock()
_resolving = threading.local()
_MISSING = object()


def set_update_queue(q):
    global _update_queue
    _update_queue = q


def set_resolver(func):
    """Register the expansion function used by resolve_gd (wired by
    env_init; breaks the params <-> globdict import cycle)."""
    global _resolver
    _resolver = func


def gd_generation():
    return _generation


def invalidate_cache():
    """Signal a direct global_dict mutation: resolved values are stale."""
    global _generation
    with _cache_lock:
        _generation += 1
        _resolved_cache.clear()


def _has_markers(value):
    if isinstance(value, str):
        return "$(" in value or "<|" in value
    if isinstance(value, dict):
        return any(_has_markers(k) or _has_markers(v)
                   for k, v in value.items())
    if isinstance(value, list):
        return any(_has_markers(v) for v in value)
    return False


def resolve_gd(name, default=None):
    """gd() with $()/<| |> resolved at read time against the live global
    dict; memoized per generation. A resolution cycle keeps the declared
    text, like the capped expansion loop."""
    with global_dict_lock:
        if name not in global_dict:
            return default
        raw = global_dict[name]
    if _resolver is None or not _has_markers(raw):
        return raw
    in_flight = getattr(_resolving, "names", None)
    if in_flight is None:
        in_flight = _resolving.names = set()
    if name in in_flight:
        return raw
    with _cache_lock:
        cached = _resolved_cache.get(name)
        if cached is not None and cached[0] == _generation:
            return cached[1]
        generation = _generation
    in_flight.add(name)
    try:
        value = _resolver(raw)
    finally:
        in_flight.discard(name)
    with _cache_lock:
        if generation == _generation:
            _resolved_cache[name] = (generation, value)
    return value


def _push_update(key, value):
    if _update_queue is None or key.startswith("_"):
        return
    try:
        json.dumps(value)
        _update_queue.put({"type": "gd_update", "key": key, "value": value})
    except (TypeError, ValueError):
        pass


def _push_delete(key):
    if _update_queue is None or key.startswith("_"):
        return
    _update_queue.put({"type": "gd_delete", "key": key})


# Global dictionnary helper functions
def gd(name, default=None):
    ''' Function which returns a variable from the global dictionary of testium

    :param name: The name of the element to return.
    :type name: str
    :param default: The default value returned by the function if the item
                    has not been found in the global dictionary (``None`` by default).
    :type default: object
    :return: The value of the item of the global dictionary or the default value.
    :rtype: object
    '''
    with global_dict_lock:
        return global_dict.get(name, default)

def setgd(name, value):
    ''' Function which updates a variable from the global dictionary of testium

    :param name: The name of the element to set.
    :type name: str
    :param value: The object to include in the global dictionary.
    :type name: str
    :return: No returned value
    '''
    with global_dict_lock:
        global_dict.update({name: value})
    invalidate_cache()
    _push_update(name, value)

def delgd(name):
    ''' Function which removes a variable from the global dictionary of testium

    :param name: The name of the element to be removed.
    :type name: str
    :return: No returned value
    '''
    with global_dict_lock:
        try:
            del global_dict[name]
        except:
            pass
    invalidate_cache()
    _push_delete(name)

def cleargd():
    with global_dict_lock:
        if global_dict is not None:
                global_dict.clear()
    invalidate_cache()

