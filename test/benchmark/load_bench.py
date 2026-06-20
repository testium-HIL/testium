#!/usr/bin/env python3
"""Time the testium *load* pipeline on a given ``.tum`` tree.

It drives the real loader code (``TestProcess._load_initial_params`` /
``_load_test`` then ``TestSet(...)``) in-process, so the numbers track the
production path and stay honest as the code evolves. Execution is never
triggered — we stop exactly where ``Batch`` would report the test as *loaded*.

Reported per run, over ``--repeat`` iterations (min is the headline, least
noisy):

    initial   first pass: discover config files (template+YAML, no includes)
    loadtest  config-file fixpoint loop + full recursive include/template/YAML
    build     TestSet construction: the load_test_recursively tree build
    total     sum of the three

Plus instrumentation counters (exact call counts, wall time) for the two
hot leaves the optimisation axes target:

    templates  jinja template_to_test() calls   (axis 1 compile cache, axis 2 tempfile)
    yaml       yaml_load() parses               (axis 3 C loader)

template time is exclusive (one file render); yaml time is wall-inclusive of
nested includes, so lean on the *counts* for attribution.

Must run inside the project venv (jinja2, pyyaml, telnetlib3, ...). The
benchmark profiles contain no ``<| |>`` so the external eval process is not
needed; pass --with-eval to start it for faithfulness on eval-heavy trees.

Usage (see run.sh for the convenience wrapper):
    test/tmp/.venv/bin/python3 test/benchmark/load_bench.py [--repeat 5] <main.tum>
"""
import argparse
import os
import statistics
import sys
from queue import Queue
from time import perf_counter

# --- bootstrap: src/testium for flat imports, src for `import testium` --------
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "src", "testium"))

import api.testium as tm  # noqa: E402
from interpreter.utils.test_init import env_init, apply_overrides  # noqa: E402
from interpreter.utils.test_ctrl import TestSetController  # noqa: E402
from interpreter.process import TestProcess  # noqa: E402
from interpreter.test_set import TestSet  # noqa: E402
from interpreter.utils.py_eval import eval_process_init  # noqa: E402
from interpreter.utils.api_srv import api_request  # noqa: E402

# --- instrumentation: count + time the two hot leaves -------------------------
import interpreter.process as _proc  # noqa: E402
import interpreter.utils.include as _inc  # noqa: E402
import interpreter.utils.test_init as _ti  # noqa: E402
import interpreter.utils.template as _tpl  # noqa: E402
import interpreter.utils.yaml_load as _yl  # noqa: E402

_C = {"tpl_n": 0, "tpl_t": 0.0, "yaml_n": 0, "yaml_t": 0.0}
_orig_tpl = _tpl.template_to_test
_orig_yaml = _yl.yaml_load


def _wrap_tpl(*a, **k):
    t = perf_counter()
    try:
        return _orig_tpl(*a, **k)
    finally:
        _C["tpl_t"] += perf_counter() - t
        _C["tpl_n"] += 1


def _wrap_yaml(*a, **k):
    t = perf_counter()
    try:
        return _orig_yaml(*a, **k)
    finally:
        _C["yaml_t"] += perf_counter() - t
        _C["yaml_n"] += 1


# rebind in every module that did `from ... import template_to_test / yaml_load`
for _m in (_proc, _inc):
    _m.template_to_test = _wrap_tpl
for _m in (_proc, _inc, _ti):
    _m.yaml_load = _wrap_yaml


def _reset_counters():
    _C.update(tpl_n=0, tpl_t=0.0, yaml_n=0, yaml_t=0.0)


def load_once(tp, fname, test_dir):
    """One full load (no execution). Returns (initial, loadtest, build) seconds."""
    t0 = perf_counter()
    init_pf, gv = tp._load_initial_params(test_dir)
    t1 = perf_counter()
    test_dict, _pf = tp._load_test(init_pf, gv)
    t2 = perf_counter()
    TestSet(fname, test_dict, Queue())
    t3 = perf_counter()
    return (t1 - t0, t2 - t1, t3 - t2)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("main_tum", help="path to the generated main.tum")
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--with-eval", action="store_true",
                    help="start the external eval process (needed only for <| |> at load)")
    ap.add_argument("--quiet", action="store_true",
                    help="silence the loader's INFO output during runs")
    args = ap.parse_args()

    fname = os.path.abspath(args.main_tum)
    if not os.path.isfile(fname):
        ap.error(f"not found: {fname}")
    test_dir = os.path.dirname(fname)

    env_init()
    apply_overrides({}, {})

    eval_proc = None
    if args.with_eval:
        eval_proc = eval_process_init(api_request, 10, test_dir)
        eval_proc.start()
        eval_proc.wait_ready(10)

    if args.quiet:
        # the loader prints a couple of INFO lines per config file; mute stdout
        # around the measured section to avoid I/O skew.
        devnull = open(os.devnull, "w")
        real_stdout = sys.stdout

    tp = TestProcess(fname, Queue(), TestSetController(),
                     config_files=[], defines={}, gui_defaults={}, text_mode=True)

    samples = []  # list of (initial, loadtest, build)
    last_counters = None
    try:
        for r in range(args.repeat):
            _reset_counters()
            if args.quiet:
                sys.stdout = devnull
            try:
                samples.append(load_once(tp, fname, test_dir))
            except RecursionError:
                if args.quiet:
                    sys.stdout = real_stdout
                print(f"file      : {fname}")
                print("ERROR     : RecursionError during load — the include "
                      "nesting is too deep for the recursive loader.\n"
                      "            (each include level costs ~10 stack frames; "
                      "raise sys.setrecursionlimit to probe further.)")
                return 2
            except Exception as e:  # noqa: BLE001 - report, don't crash the bench
                if args.quiet:
                    sys.stdout = real_stdout
                print(f"file      : {fname}")
                print(f"ERROR     : load failed: {type(e).__name__}: {e}")
                return 2
            finally:
                if args.quiet:
                    sys.stdout = real_stdout
            last_counters = dict(_C)
    finally:
        if eval_proc is not None:
            eval_proc.stop()
            eval_proc.join()
        if args.quiet:
            devnull.close()

    initial = [s[0] for s in samples]
    loadtest = [s[1] for s in samples]
    build = [s[2] for s in samples]
    total = [sum(s) for s in samples]

    def stat(xs):
        return min(xs), statistics.median(xs)

    print(f"file      : {fname}")
    print(f"repeats   : {args.repeat}   (showing  min | median, seconds)")
    print(f"{'phase':<10}{'min':>12}{'median':>12}")
    for name, xs in (("initial", initial), ("loadtest", loadtest),
                     ("build", build), ("total", total)):
        mn, md = stat(xs)
        print(f"{name:<10}{mn:>12.4f}{md:>12.4f}")
    if last_counters:
        print("counters  (last run):")
        print(f"  templates : {last_counters['tpl_n']:>7d} calls   "
              f"{last_counters['tpl_t']:>8.4f}s  (exclusive: jinja compile+render+tempfile)")
        print(f"  yaml      : {last_counters['yaml_n']:>7d} parses  "
              f"{last_counters['yaml_t']:>8.4f}s  (inclusive of nested includes)")


if __name__ == "__main__":
    sys.exit(main() or 0)
