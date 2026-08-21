
def make_columns():
    """Per-tree column table (name, index, size). The duration column is
    always present; its visibility follows the preference at run time."""
    return {
        'name':     {'name': 'Name',   'index': 0, 'size': 300},
        'pause':    {'name': '',       'index': 1, 'size': 24},
        'type':     {'name': 'Type',   'index': 2, 'size': 150},
        'status':   {'name': '',       'index': 3, 'size': 50},
        'duration': {'name': 'Time',   'index': 4, 'size': 50},
        'failure':  {'name': 'Fails',  'index': 5, 'size': 50},
        'desc':     {'name': 'Result', 'index': 6, 'size': 100},
    }
