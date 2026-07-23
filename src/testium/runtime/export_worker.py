"""Host-side report exporter worker.

Runs third-party ``testium.exporters`` entry-point plugins on the *host*
Python interpreter (the one resolved by ``bins.python_bin()``), where the
user can pip-install them — the bundled interpreter of the Flatpak /
AppImage / PyInstaller channels is read-only.

Stdlib-only: launched as ``python3 export_worker.py '<json>'`` with no
PYTHONPATH requirement. The JSON argument holds:
    format    : export format name (entry-point name)
    db        : path to a temp SQLite copy of the report database
    path      : output file path (already expansed)
    pats      : list of LIKE filters on test_name
    keys      : list of LIKE filters on report_key
    no_header : bool
    name      : report name

Exit codes:
    0 : export done
    1 : exporter error (message on stderr)
    3 : unknown format — the available plugin names are printed on stdout
        as ``__TESTIUM_EXPORT_FORMATS__=name1,name2``
"""

import json
import sqlite3
import sys

FORMATS_SENTINEL = "__TESTIUM_EXPORT_FORMATS__="
EXIT_UNKNOWN_FORMAT = 3


def main():
    params = json.loads(sys.argv[1])
    fmt = params["format"]

    from importlib.metadata import entry_points
    eps = {ep.name: ep for ep in entry_points(group="testium.exporters")}

    if fmt not in eps:
        print(FORMATS_SENTINEL + ",".join(sorted(eps)))
        return EXIT_UNKNOWN_FORMAT

    try:
        cls = eps[fmt].load()
    except Exception as e:
        print(f'Cannot load exporter "{fmt}" '
              f'({eps[fmt].value}): {type(e).__name__}: {e}', file=sys.stderr)
        return 1

    con = sqlite3.connect(params["db"])
    try:
        cls(params["name"], con, params["path"],
            params["pats"], params["keys"], params["no_header"])
    except Exception as e:
        print(f'Exporter "{fmt}" failed: {type(e).__name__}: {e}',
              file=sys.stderr)
        return 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
