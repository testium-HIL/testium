# Quick start

Five minutes from zero to a passing test.

## Install

From a checkout of the repository:

```sh
./run.sh --version    # Linux
run.bat               # Windows cmd
```

The wrapper creates a Python virtual environment on first run and verifies
testium starts. If you prefer a manual install, see the README.

## Your first test

Create `hello.tum`:

```yaml
main:
    name: hello world
    steps:
        - check:
            name: 1 + 1 makes 2
            values:
                - <| 1 + 1 == 2 |>
```

Run it in batch mode:

```sh
./run.sh -b -- hello.tum
```

You should see something like:

```
-----> step "1 + 1 makes 2" started
Check passed
<----- step "1 + 1 makes 2" finished: PASS
Test run success.
```

Replace `==` with `!=` and re-run — the step now ends with **FAIL** and
the process exits with code 1.

## Open it in the GUI

```sh
./run.sh hello.tum
```

The test tree appears in the left panel; click *Run test* in the toolbar.
Each item turns green or red live as it executes. Use `F1` on a selected
item to open its detail panel.

## Where to go next

* [`doc/tutorial.md`](tutorial.md) — a guided walk-through of the most
  common test items (`py_func`, `let`, `group`, `condition`, `report`).
* [`doc/examples/`](examples/) — runnable `.tum` snippets covering one
  feature each.
* [`doc/manual/testium_manual.pdf`](manual/testium_manual.pdf) —
  full reference manual.
