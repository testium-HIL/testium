import py_func.tm as tm


def check_log_timestamps(report_dir, item, step, min_gap):
    # The per-item JUnit report (written by the report items in
    # items/report.tum) keeps every PASS step's full log. The console test
    # emits tsline_1/2/3 two seconds apart, leaves them buffered, then
    # drains them with one read_until: the [HH:MM:SS name] stamps in the
    # step log must keep that 2 s spacing — the reception time, the
    # contract the file log already honours — not collapse onto the drain
    # time.
    import os
    import re
    import xml.etree.ElementTree as ET

    path = os.path.join(report_dir, "{}_PASS.junit".format(item))
    root = ET.parse(path).getroot()
    log = None
    for tc in root.iter("testcase"):
        if tc.get("name") == step:
            log = tc.get("log")
            break
    if log is None:
        raise AssertionError(
            "step {!r} not found in {}: it did not PASS, so its log "
            "cannot be inspected".format(step, path))
    stamps = {}
    # The shell prompt may precede tsline_1 on its line.
    for m in re.finditer(r"\[(\d{2}:\d{2}:\d{2}) \w+\].*?\b(tsline_\d)\s*$",
                         log, re.M):
        h, mn, s = m.group(1).split(":")
        stamps[m.group(2)] = int(h) * 3600 + int(mn) * 60 + int(s)
    missing = [n for n in ("tsline_1", "tsline_2", "tsline_3")
               if n not in stamps]
    if missing:
        raise AssertionError(
            "line(s) {} not found in the log of step {!r} ({})".format(
                missing, step, path))
    gap = stamps["tsline_3"] - stamps["tsline_1"]
    if gap < int(min_gap):
        raise AssertionError(
            "tsline_3 - tsline_1 = {} s (< {} s) in the log of step "
            "{!r}: the stamps collapsed onto the drain time instead of "
            "keeping the 2 s reception spacing ({} vs {})".format(
                gap, min_gap, step,
                stamps["tsline_1"], stamps["tsline_3"]))
    return 0
