import libs.testium as libtm


def check_os(expected_os):
    result = libtm.OS()
    assert result == expected_os, f"Expected {expected_os!r}, got {result!r}"
    return 0


def check_get_main_dir():
    d = libtm.get_main_dir()
    assert isinstance(d, str) and len(d) > 0
    return 0


def check_timestamp_as_sec_conversion():
    assert libtm.timestamp_as_sec(0) == 0.0
    assert libtm.timestamp_as_sec(10000) == 1.0
    assert libtm.timestamp_as_sec(5000) == 0.5
    return 0


def check_timestamp():
    libtm.init_timestamp()
    t = libtm.timestamp()
    assert isinstance(t, int) and t >= 0
    ts = libtm.timestamp_as_sec()
    assert isinstance(ts, float) and ts >= 0.0
    return 0
