# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Duration attribute parsing shared by the test items (sleep timeout,
plot periodic period)."""

import re

from runtime.tum_except import ETUMRuntimeError

_NUMBER = r"\d+(?:\.\d+)?"
_UNITS = re.compile(
    rf"\s*(?:(?P<day>{_NUMBER})d)?"
    rf"\s*(?:(?P<hour>{_NUMBER})h)?"
    rf"\s*(?:(?P<minute>{_NUMBER})m)?"
    rf"\s*(?:(?P<second>{_NUMBER})s)?\s*",
    flags=re.IGNORECASE)
_SCALE = {"day": 86400, "hour": 3600, "minute": 60, "second": 1}


def parse_duration(value, origin):
    """Seconds as a float from a number or a string: a decimal number
    ("1.5") or units in the order days, hours, minutes, seconds ("1d 2h
    30m 15s", decimals allowed). Raises ETUMRuntimeError otherwise."""
    seconds = None
    if isinstance(value, bool):
        seconds = None
    elif isinstance(value, (int, float)):
        seconds = float(value)
    elif isinstance(value, str):
        text = value.strip()
        try:
            seconds = float(text)
        except ValueError:
            m = _UNITS.fullmatch(text)
            if m is not None and any(m.groupdict().values()):
                seconds = sum(float(v) * _SCALE[k]
                              for k, v in m.groupdict().items() if v)
    if seconds is None or seconds < 0:
        raise ETUMRuntimeError(
            f"{origin}: expected a duration in seconds or 'Nd Nh Nm Ns', "
            f"got {value!r}.")
    return seconds
