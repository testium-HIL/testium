# Quick start

Five minutes from zero to a passing test.

## Install

```sh
pip install 'testium-hil[qt]'
testium --version
```

The PyPI project is named `testium-hil`; the installed command is
`testium`. The bare `testium-hil` (without `[qt]`) is the batch-only
core. For other installation methods (pre-built binaries, source
checkout), see the README.

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
testium -b hello.tum
```

You should see something like:

```
-----> step "1 + 1 makes 2" started
Check passed
<----- step "1 + 1 makes 2" finished: PASS
Test run success.
```

Replace `==` with `!=` and re-run: the step now ends with FAIL and
the process exits with code 1.

## Open it in the GUI

```sh
testium hello.tum
```

The test tree appears in the left panel; click *Run test* in the toolbar.
Each item turns green or red live as it executes. Click an item to see
its source in the *Step info* panel; `F1` brings the *Variables* panel
to the front.

## Where to go next

* [`doc/tutorial.md`](tutorial.md): a guided walk-through of the most
  common test items (`py_func`, `let`, `group`, `condition`, `report`).
* [`doc/console_tutorial.md`](console_tutorial.md): drive a shell, an
  ssh session or serial equipment from a test.
* [`doc/examples/`](examples/): runnable `.tum` snippets covering one
  feature each.
* [`doc/manual/testium_manual.pdf`](manual/testium_manual.pdf):
  full reference manual.
