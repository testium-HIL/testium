import time
import py_func.tm as tm


def sleep_func(duration):
    time.sleep(float(duration))
    return 0


def check_duration(item_name, max_duration):
    t0 = tm.gd(f"ts_start_{item_name}")
    t1 = tm.gd(f"ts_end_{item_name}")
    duration = tm.timestamp_as_sec(t1 - t0)
    if duration < float(max_duration):
        return 0
    return 1
