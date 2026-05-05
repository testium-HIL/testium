# Tutorial — testing a small Python utility

This walk-through builds, step by step, a testium campaign that exercises
a small Python module. Each section adds one feature; you can follow
along by editing a single `.tum` file and re-running it.

If you have not yet run testium, start with [`quick_start.md`](quick_start.md).

## The code under test

Create `calc.py` next to your `.tum` file:

```python
def add(a, b):
    return a + b

def divide(a, b):
    return a / b
```

## Step 1 — a static check

The simplest item is `check`: it evaluates an expression and the test
passes iff the expression is truthy. Create `tutorial.tum`:

```yaml
main:
    name: calc.py campaign
    steps:
        - check:
            name: addition is correct
            values:
                - <| 2 + 3 == 5 |>
```

The `<| ... |>` markers turn the body into a Python expression evaluated
at run time. Run it:

```sh
./run.sh -b -- tutorial.tum
```

## Step 2 — call your code with `py_func`

`check` only sees Python literals; to exercise `calc.py` we need a
`py_func` item. Replace the step:

```yaml
        - py_func:
            name: add 2 and 3
            file: calc.py
            func_name: add
            param: [2, 3]
            expected_result: 5
```

`expected_result` makes the item PASS only when the function returns
exactly that value.

The result is also stored in the global dict under `pfn_<name>`
(here `pfn_add 2 and 3`).

Anywhere in a `.tum`, `$(key)` is replaced at runtime by the value
stored in the global dict under `key`. A subsequent step can read the
result back with `$(pfn_<name>)`:

```yaml
        - check:
            name: result was 5
            values:
                - <| $(pfn_add 2 and 3) == 5 |>
```

## Step 3 — group several checks

Wrap the steps in a `group` to keep them visually together and let
testium report a per-group status:

```yaml
main:
    name: calc.py campaign
    steps:
        - group:
            name: add
            steps:
                - py_func:
                    name: 2 + 3
                    file: calc.py
                    func_name: add
                    param: [2, 3]
                    expected_result: 5
                - py_func:
                    name: -1 + 1
                    file: calc.py
                    func_name: add
                    param: [-1, 1]
                    expected_result: 0
        - group:
            name: divide
            steps:
                - py_func:
                    name: 6 / 2
                    file: calc.py
                    func_name: divide
                    param: [6, 2]
                    expected_result: 3.0
```

A group fails as soon as one of its steps fails (set
`stop_on_failure: false` to keep going).

## Step 4 — define a variable with `let`

Avoid hard-coding the same number twice with a variable:

```yaml
        - let:
            name: define numerator
            values:
                - num: 6
        - py_func:
            name: divide num by 2
            file: calc.py
            func_name: divide
            param:
                - $(num)
                - 2
            expected_result: 3.0
```

`$(num)` expands to the global dict entry — when the stored value is a
number it is substituted as a number, no need to wrap it in `<| ... |>`.

## Step 5 — conditional execution

Skip a step when a condition is false:

```yaml
        - py_func:
            name: divide by zero only on linux
            condition: <| "$(os)" == "Linux" |>
            file: calc.py
            func_name: divide
            param: [1, 0]
```

Items skipped this way report `SKIP` and do not affect the overall
result.

## Step 6 — generate a report

Add a `report` block at the root of the file:

```yaml
main:
    name: calc.py campaign
    steps:
        # ... your steps here ...

report:
    enabled: true
    log_stored: true
    export:
        - junit:
            path: ./reports
            file_name: calc.xml
        - html:
            path: ./reports
            file_name: calc.html
```

The `path` directory must exist before the test runs — testium does not
create it. Create it once:

```sh
mkdir -p reports
```

Re-run the test — `./reports/calc.xml` (CI-friendly) and
`./reports/calc.html` (human-friendly) are produced. Set
`log_stored: true` to include each item's captured stdout.

## Step 7 — share state between calls

By default each `py_func` runs in its own short-lived subprocess.
To keep state across calls, use `context_id`:

```yaml
        - py_func:
            name: open
            file: calc.py
            func_name: open_resource
            context_id: my_ctx
        - py_func:
            name: use
            file: calc.py
            func_name: use_resource
            context_id: my_ctx
```

Both steps share the same persistent Python interpreter, so `calc.py`
can store any object in module-level globals or in `tm.setgd()`.

To share data without `context_id`, write it to the testium global dict
via the JSON-RPC bridge:

```python
import py_func.tm as tm

def producer():
    tm.setgd("computed", 42)

def consumer():
    return tm.gd("computed")
```

## Where to go next

* [`doc/examples/`](examples/) — one runnable `.tum` per feature
  (cycles, dialogs, console, plots, parallel, run-of-tum, …).
* [`doc/manual/testium_manual.pdf`](manual/testium_manual.pdf) — full
  reference manual covering every test item, every attribute and the
  YAML syntax extensions.
