# Tutorial — debugging a `py_func` step by step

This tutorial shows how to debug the Python code of a `py_func` test
item from your IDE: breakpoints, stepping, variable inspection — while
the test runs normally in testium.

It works with every install channel (source, wheel, PyInstaller,
Flatpak, AppImage): the function always runs on the host Python
(`python_bin`), and that is where the debugger attaches.

## How it works

With `debug: true` on a `py_func` item, the subprocess running your
function starts a [debugpy](https://github.com/microsoft/debugpy)
listener on `localhost:5678` and **waits** for a debugger to attach
before calling the function. The test log shows:

```
py_func waiting for the debugger on localhost:5678 — attach from your IDE, or Stop to cancel
```

You attach from the IDE, the function starts, and execution stops on
the breakpoints you set in your `.py` file.

## Step 1 — install debugpy

Install debugpy with the host Python — the `python_bin` interpreter,
the same one running your functions:

```sh
<python_bin> -m pip install debugpy
```

As for `py_func` dependencies and pytest, this is a plain terminal
command on the machine; nothing changes inside testium.

## Step 2 — mark the item

Take a test with a function to inspect:

`process.py`:

```python
def process(raw):
    values = [int(v) for v in raw.split(";")]
    total = sum(values)
    return total / len(values)
```

`test.tum` — add `debug: true` to the item:

```yaml
main:
    name: my test
    steps:
        - py_func:
            name: average
            file: process.py
            func_name: process
            param: ["3;5;10"]
            debug: true
            expected_result: 6.0
```

## Step 3 — configure the IDE

VSCode: add an *attach* configuration to `.vscode/launch.json` (create
the file if needed):

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Attach to py_func",
            "type": "debugpy",
            "request": "attach",
            "connect": {"host": "localhost", "port": 5678},
            "justMyCode": true
        }
    ]
}
```

Any DAP-capable editor works the same way — the target is a debugpy
server on `localhost:5678`.

## Step 4 — debug

1. Open `process.py` in the IDE and set a breakpoint (e.g. on the
   `total = sum(values)` line).
2. Run the test (GUI Start or batch `testium -b test.tum`). The run
   pauses at the item and the log shows the waiting message.
3. Press F5 in VSCode ("Attach to py_func"). The function starts and
   stops on your breakpoint: step (F10/F11), inspect variables, use the
   debug console.
4. Continue (F5): the function finishes, testium resumes the test.

To cancel a waiting item, press Stop in testium: the item fails with
"py_func aborted on stop request" and the run continues its normal stop
path. An item left waiting fails by itself after one hour.

## Debugging several items

Each `py_func` item without `context_id` runs in a fresh subprocess:
every `debug: true` item waits for its own attach (the IDE reconnects
each time — in VSCode just press F5 again).

With `context_id`, the shared subprocess opens the listener once and
the debugger **stays attached** across the items: the next `debug: true`
items log "debugger already attached." and run without pausing. If the
IDE disconnects in between, the next one waits again.

Only mark the items you want to inspect — the others run normally.

## Changing the port

The listener port comes from the `py_func_debug_port` global variable
(default 5678). Set it from a configuration file or the command line,
and align `launch.json`:

```sh
testium -b test.tum -d py_func_debug_port=5679
```

With `context_id`, the first `debug: true` item fixes the port for the
whole life of the shared subprocess; a later change is ignored with a
warning.

## Remote testium

The listener only accepts local connections. If testium runs on another
machine (a test bench), open an SSH tunnel and attach as if local:

```sh
ssh -L 5678:localhost:5678 bench-host
```

## Troubleshooting

* `debugpy is not installed on the host interpreter used by testium
  (python_bin)...` — install debugpy as in step 1, with the exact
  interpreter used by testium (check the `python_bin` global; if it
  points to a venv, install into that venv).
* `debugpy could not listen on localhost:5678 (...). Is the port
  free?` — another program (or another testium run) holds the port; set
  `py_func_debug_port` to a free one.
* The IDE attaches but no breakpoint is hit — check the breakpoints are
  in the file actually referenced by `file:` (paths are resolved
  relative to the test directory), and that `justMyCode` is not hiding
  the frames you expect.
* Function prints may appear both in the IDE debug console and the
  testium log when the debugger's `redirectOutput` option is on; this
  is harmless.

## Where to go next

* Manual, `py_func` chapter — the `debug` attribute reference, the
  `context_id` execution model and the interpreter environment
  variables.
