

def clear_recursively(obj):
    if not isinstance(obj, (dict, list)):
        del obj
        return
    if isinstance(obj, list):
        for o in obj:
            clear_recursively(o)
    else:
        for key in list(obj.keys()):
            clear_recursively(obj[key])
            o = obj.pop(key, None)
