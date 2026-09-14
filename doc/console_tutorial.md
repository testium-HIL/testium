# Tutorial: driving a console

This walk-through drives a local shell from a test: run commands, check
their output, synchronize on what the device prints. The same item
drives ssh sessions, serial ports and raw TCP equipment.

No hardware is needed: the `terminal` protocol starts a shell on your
machine. Everything below works unchanged on Linux and Windows.

## Step 1: open a console and run a command

Create `console.tum`:

```yaml
main:
    name: console tutorial
    steps:
        - console:
            name: open
            console_name: shell
            steps:
                - open:
                    protocol: terminal

        - console:
            name: first command
            console_name: shell
            steps:
                - exec: echo hello console

        - console:
            name: close
            console_name: shell
            steps:
                - close:
```

Run it (`testium -b console.tum`). The `exec` action sends the command,
then waits until it is finished: testium appends a unique marker to the
command line and reads until the marker comes back. You never have to
guess a prompt or add a sleep.

`exec` works identically on Windows (`cmd.exe`) and Linux (`bash`):
testium picks the marker syntax matching the shell, so the test file
above runs unmodified on both.

## Step 2: check the output

The text read by `exec` (marker removed) becomes the item result, so
`process_result` can check it:

```yaml
        - console:
            name: checked command
            console_name: shell
            steps:
                - exec:
                    cmd: echo the answer is 42
                    timeout: 10
                    process_result: "'42' in r'''$(result)'''"
```

Without `timeout`, `exec` waits forever. A command that never returns
to the shell (an editor, a password prompt) never prints the marker:
give a `timeout` to fail cleanly instead.

The output is also stored in the global variable `cn_<item name>`, for
later items:

```yaml
        - check:
            name: output recorded
            values:
                - <| "42" in r"""$(cn_checked command)""" |>
```

## Step 3: consoles that are not shells

Serial equipment, telnet devices and applications with their own prompt
do not run a shell: there is nowhere to inject a marker. Synchronize
those by hand with `writeln` and `read_until`:

```yaml
        - console:
            name: manual synchronization
            console_name: shell
            steps:
                - writeln: echo done_marker
                - read_until: {expected: done_marker, timeout: 5}
```

`read_until` also accepts a list of patterns (succeeds on any) and
regular expressions:

```yaml
                - read_until:
                    expected: 'version \d+\.\d+'
                    regex: true
                    timeout: 5
```

Add `no_fail: true` to tolerate a timeout, `mute: true` to keep the
exchanged text out of the log.

## Step 4: dialects and line endings

The `open` action takes two parameters that matter beyond the local
terminal:

* `dialect`: the shell family `exec` speaks: `sh` (also fine for zsh,
  fish, busybox), `cmd`, `powershell` or `none`. It is guessed for the
  `terminal` and `ssh` protocols; the device protocols (telnet, rawtcp,
  serial) default to `none`, where `exec` refuses with a clear message:
  use `writeln` + `read_until` there. Set it yourself when the guess is
  wrong: a Linux shell on a serial port (`sh`), an ssh server on a
  Windows machine (`powershell`).
* `newline`: the line ending `writeln` appends: `lf` (default),
  `crlf` or `cr`. Serial modems and some network equipment expect
  `crlf`.

```yaml
                - open:
                    protocol: terminal
                    shell: pwsh
                    dialect: powershell
```

```yaml
                - open:
                    protocol: serial
                    serial_port: /dev/ttyUSB0
                    serial_baudrate: 115200
                    newline: crlf
```

## Step 5: the same test over ssh

Replace the `open` parameters and nothing else:

```yaml
                - open:
                    protocol: ssh
                    ssh_host: $(bench_ip)
                    ssh_user: operator
```

`exec` behaves exactly as on the local terminal. The marker travels in
the session, so even a shell started inside the ssh session (`su`,
another `ssh` hop) keeps working. The ssh protocol is not available on
Windows hosts.

## Where to go next

* Manual, `console` chapter: every protocol and parameter.
* [`doc/examples/`](examples/): `example_items.tum` includes a runnable
  console group.
