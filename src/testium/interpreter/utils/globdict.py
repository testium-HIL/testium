import json
from threading import Lock


global_dict = {}

global_dict_lock = Lock()

_update_queue = None


def set_update_queue(q):
    global _update_queue
    _update_queue = q


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
    _push_delete(name)

def cleargd():
    with global_dict_lock:
        if global_dict is not None:
                global_dict.clear()

