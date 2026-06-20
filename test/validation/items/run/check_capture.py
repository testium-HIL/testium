import py_func.tm as tm


def assert_captured():
    """The sub-run log stored by `run` via store_result must be in the gdict."""
    log = tm.gd("captured_log", "")
    assert "Test run success." in log, \
        "captured sub-run log not reachable from the gdict (store_result)"
    return 0
