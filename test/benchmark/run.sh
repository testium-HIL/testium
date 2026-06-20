#!/bin/bash
# Load-time benchmark driver: generate synthetic .tum trees and time the
# testium load pipeline on them, using the project venv.
#
# Usage:
#   ./test/benchmark/run.sh                     # default matrix (all profiles)
#   ./test/benchmark/run.sh <profile> <size>    # one profile at one size
#   REPEAT=10 ./test/benchmark/run.sh repeat 2000
#
# Profiles: flat includes repeat jinja deep mix   (see gen_bench_test.py)
#
# Generated trees go under test/benchmark/cases/ (git-ignored). The numbers
# are wall-clock; run on an otherwise idle machine and compare min values.
set -e

SCRIPT_DIR="$(realpath "$(dirname "$(readlink -f "$0")")")"
PROJECT_DIR="$(realpath "$SCRIPT_DIR/../..")"
VPY="$PROJECT_DIR/test/tmp/.venv/bin/python3"
CASES="$SCRIPT_DIR/cases"
REPEAT="${REPEAT:-5}"

if [ ! -x "$VPY" ]; then
    echo "ERROR: project venv not found at $VPY — run ./run.sh once to create it." >&2
    exit 1
fi

bench() {
    local profile="$1" size="$2"
    local out="$CASES/${profile}_${size}"
    local main
    main="$("$VPY" "$SCRIPT_DIR/gen_bench_test.py" --profile "$profile" --size "$size" --out "$out")"
    echo "===== profile=$profile size=$size ====="
    "$VPY" "$SCRIPT_DIR/load_bench.py" --repeat "$REPEAT" --quiet "$main"
    echo
}

if [ $# -eq 2 ]; then
    bench "$1" "$2"
    exit 0
fi

# Default matrix. 'deep' is kept small: the recursive loader hits Python's
# recursion limit around ~90 nested include levels.
bench flat     2000
bench includes 1000
bench repeat   1000
bench jinja    2000
bench deep     40
bench mix      300
