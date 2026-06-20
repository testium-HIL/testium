# Load-time benchmark

Measures how long *testium* takes to **load** a `.tum` test tree — template
rendering (jinja) + YAML parsing + test-tree construction — *without* executing
it. Purpose: get reproducible numbers before/after load-path optimisations, and
attribute any gain to a specific part of the pipeline.

It is meant for *very long* tests, the kind you can build with `jinja` loops and
`!include`, where load time becomes noticeable.

## Files

| File | Role |
|------|------|
| `gen_bench_test.py` | Generates a synthetic `.tum` tree (the test input). |
| `load_bench.py` | Drives the **real** loader in-process and times it. |
| `run.sh` | Convenience: generate + time across profiles, using the project venv. |
| `cases/` | Generated trees (git-ignored, recreated on demand). |

The benchmark `.tum` files are **generated**, not committed — the generator is
the artifact. They use only `let` leaves and `group` containers, so loading has
no runtime side effect (no subprocess, no `<| |>` eval) and the timing reflects
the parse/build pipeline alone.

## Quick start

```bash
# default matrix (all profiles), 5 repeats each
./test/benchmark/run.sh

# one profile at one size
./test/benchmark/run.sh repeat 2000

# more repeats for a tighter min
REPEAT=10 ./test/benchmark/run.sh includes 1000
```

`run.sh` uses the project venv at `test/tmp/.venv` (created by `./run.sh`). If it
is missing, run `./run.sh` once first.

To drive the harness directly on any `.tum` (not just generated ones):

```bash
test/tmp/.venv/bin/python3 test/benchmark/load_bench.py --repeat 5 --quiet path/to/main.tum
```

## Profiles

Each profile isolates one cost. `--size` is the profile-specific count.

| Profile | What it builds | Stresses |
|---------|----------------|----------|
| `flat` | one main file, N inline `let` steps | big YAML parse + linear object build |
| `includes` | main `!include`s N **distinct** sub-files | per-include template+YAML+tempfile, `sequence` splice |
| `repeat` | main `!include`s the **same** parametrised leaf N times | jinja **recompilation** of an identical template |
| `jinja` | one main file, `{% for %}` emitting N steps | single large render + single large parse |
| `deep` | nested includes, depth N | include recursion (see caveat) |
| `mix` | groups + jinja loop + distinct + repeated includes | realistic blend |

## Reading the output

```
phase              min      median
initial         0.1131      0.1285   <- pass 1: discover config files (no includes)
loadtest        1.0724      1.0900   <- config fixpoint loop + full recursive include load
build           0.1850      0.1976   <- TestSet: load_test_recursively tree build
total           1.3886      1.4227
counters  (last run):
  templates :    1003 calls   0.5247s  (exclusive: jinja compile+render+tempfile)
  yaml      :    1004 parses   1.4696s  (inclusive of nested includes)
```

- **min** is the headline (least noisy); median is a sanity check.
- **initial / loadtest / build** map to the three pipeline stages in
  `interpreter/process.py` and `interpreter/test_set.py`. The main file is
  rendered+parsed across `initial` *and* `loadtest` (the loader does ~3 passes).
- **templates** = number of `template_to_test()` calls and their *exclusive*
  wall time (one file render each — pure jinja compile+render+tempfile I/O).
  A high count with the same source file = recompilation, the `repeat` case.
- **yaml** = number of `yaml_load()` parses. Its time is *inclusive* of nested
  includes, so use the **count** for attribution, not the seconds.

## Mapping to the optimisation axes

| Axis (see DESIGN / discussion) | Watch | Best profile to prove it |
|--------------------------------|-------|--------------------------|
| 1 — cache compiled jinja templates | `templates` time drops, count unchanged | `repeat` |
| 2 — drop the tempfile round-trip | `templates` time drops | `includes`, `repeat`, `mix` |
| 3 — C YAML loader (libyaml) | `yaml` time / `loadtest` drops | `flat`, `jinja` |
| 6 — O(n²) sequence splice | `build` drops | `includes`, `mix` |

## How to compare before/after a change

1. Run the matrix on the current code, keep the output.
2. Apply one axis.
3. Re-run the **same** profiles/sizes; compare `min` per phase and the counters.

Change one axis at a time so the attribution is clean. Run on an idle machine
(and note the disk: on a USB stick the tempfile round-trip of axis 2 weighs
more).

## Caveat: deep includes

The loader is recursive and spends ~10 stack frames per include level, so
`deep` hits Python's `RecursionError` around ~90 nested levels. The harness
reports this cleanly instead of crashing. Real tests are *wide* (many steps /
many includes), not deep, so `includes`/`repeat`/`jinja`/`mix` are the
representative "very long" cases.

## Notes

- No execution is triggered — timing stops where `Batch` would mark the test
  *loaded*.
- The profiles contain no `<| |>`, so the external eval process is not started.
  Pass `--with-eval` to `load_bench.py` for trees that evaluate at load time.
- Numbers are machine- and disk-specific; only compare runs from the same host.
