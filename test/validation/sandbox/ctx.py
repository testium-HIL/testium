import ctx_state


def set_state(value):
    ctx_state.value = value
    return value


def get_state():
    return ctx_state.value
