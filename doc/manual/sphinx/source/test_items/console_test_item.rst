.. _sec_console_test_item:

**console** test item
============================================================

The console test item is of the form:

.. code-block:: yaml
    :caption: example of ``console`` test item usage

    - console:
        name: test name in GUI
        console_name: console name in dict
        steps:
            - open:
                protocol: telnet
                telnet_host: $(target_ip)
                telnet_port: $(target_port)
            - writeln: reset
            - read_until: {expected: U-Boot, timeout: 50}
            - write: $(boot_vxworks_1)
            - writeln: $(boot_vxworks_2)
            - read_until:
                expected: U-Boot
                timeout: 15
            - read_until:
                expected: Something that will never occur
                timeout: 5
                no_fail: True
                mute: True
            - close:

Attributes
-----------------------

Besides the common test item attributes, the console test item has specific attributes:

* ``console_name``: console instance name
* ``write_delay``: optional parameter giving the delay to wait in
  milliseconds between each character sent.
* ``steps``: a sequence of actions to be applied to the console, as listed above.

The console test item steps accept the parameters and configurations defined in the next sections.

All the following actions support the ``name`` attribute. The ``name`` is concatenated with
the step type in the *testium* GUI, and repeated in the test log and reports.

``open`` action
-------------------------

The ``open`` action initializes the console with the attributes defined as described below.
The console instance is then added to the ``console_instances`` entry of the global
variables (cf :ref:`global variables<sec_global_variables>`).

Open step accepts the following attribute:

* ``protocol``: Setting of the console protocol; supported protocols are listed
  in the table below
* The other attributes depend on the protocol in use and are listed
  in the table below. The protocol and connection parameters are
  resolved on every execution of the open action.

.. table:: console protocols
    :widths: 20, 30, 50

    +---------------+------------------------+-------------------------------------------+
    | **Protocol**  | **protocol parameter** | **Description**                           |
    +---------------+------------------------+-------------------------------------------+
    |``telnet``     | ``telnet_host``        | hostname of the target.                   |
    |               +------------------------+-------------------------------------------+
    |               | ``telnet_port``        | port of the telnet server of the target.  |
    +---------------+------------------------+-------------------------------------------+
    |``ssh``        | ``ssh_host``           | Hostname or IP address of the target.     |
    |               +------------------------+-------------------------------------------+
    |               | ``ssh_user``           | User name for the SSH connection.         |
    |               +------------------------+-------------------------------------------+
    |               | ``ssh_pwd``            | Password (optional).                      |
    +---------------+------------------------+-------------------------------------------+
    |``serial``     | ``serial_port``        | Serial port to the target.                |
    |               +------------------------+-------------------------------------------+
    |               | ``serial_baudrate``    | Baud rate of the serial connection.       |
    |               +------------------------+-------------------------------------------+
    |               | ``buffered``           | Optional boolean parameter. If ``False``, |
    |               |                        | it forces the console to read the device  |
    |               |                        | directly. Default: ``True``.              |
    +---------------+------------------------+-------------------------------------------+
    |``rawtcp``     | ``tcp_host``           | hostname of the target.                   |
    |               +------------------------+-------------------------------------------+
    |               | ``tcp_port``           | port of the rawtcp server of the target.  |
    +---------------+------------------------+-------------------------------------------+
    |``terminal``   | ``terminal_path``      | Path of the terminal console.             |
    +               +------------------------+-------------------------------------------+
    |               | ``shell``              | Shell to execute in the terminal          |
    |               |                        | Default: /usr/bin/env bash                |
    +---------------+------------------------+-------------------------------------------+

* ``log``: is available only for Telnet and Serial console and is a path to a folder or a file, where the log will be stored.
* ``newline``: line ending appended by ``writeln``: ``lf`` (default),
  ``crlf`` or ``cr``. Use ``crlf`` or ``cr`` for serial devices and
  network equipment expecting carriage returns.
* ``dialect``: shell dialect used by the ``exec`` action: ``sh``,
  ``cmd``, ``powershell`` or ``none``. By default it is guessed from
  the shell for the ``terminal`` and ``ssh`` protocols, and ``none``
  for the device protocols (telnet, rawtcp, serial).

``close`` action
---------------------------

The ``close`` action closes the console devices and removes its instance from
the ``console_instances`` list accessible in the global variables
(cf :ref:`global variables<sec_global_variables>`).

No parameters required for this action.

``write`` action
---------------------------

``write`` action takes as parameter the string to be written on the console.

``writeln`` action
-------------------------

writeln function is similar to the write function except that a '\n' (newline) character is sent at the end of the string to be written.

``exec`` action
-------------------------

The ``exec`` action sends a command to a shell console and waits until
the command is finished. *testium* appends a unique per-call marker to
the command line; seeing the marker in the output means the command
completed. This works identically for a local shell, an SSH session or
a shell started inside another shell — no prompt configuration needed.

.. code-block:: yaml
    :caption: exec: short and detailed forms

    - exec: make all

    - exec:
        cmd: ./deploy.sh
        timeout: 30
        process_result: "'done' in r'''$(result)'''"

Parameters:

* ``cmd``: the command line to run (single line). The short form
  ``- exec: <command>`` is equivalent to ``- exec: {cmd: <command>}``.
* ``timeout``: seconds before giving up (negative or absent: infinite).
  An interactive command that never returns to the shell (an editor, a
  password prompt) never prints the marker; the timeout is the safety
  net.
* ``mute``: if ``True``, the exchanged data is not logged.

The command output (marker removed) is stored in the item result and in
the global variable ``cn_<test_name>``, like ``read_until``.

The console must have a shell ``dialect`` (see the ``open`` action). On
a ``none`` console — network equipment, an application managing its own
prompt — ``exec`` fails with an explicit message: synchronize those
with ``writeln`` and ``read_until`` instead. A shell started inside the
session that speaks another dialect (PowerShell launched from bash) is
not handled by ``exec``.

The marker travels in the console stream, so it is visible in the
console logs; use ``mute`` to hide the exchange.

``read_until`` action
----------------------------

The ``read_until`` action waits for a string pattern from the console.
Its parameters are listed below:

* ``expected``: the value to wait for. A list is also accepted; the
  action succeeds when any entry of the list is seen.
* ``regex``: Boolean value (default ``False``). When ``True``, each
  ``expected`` entry is a Python regular expression searched in the
  received text.
* ``timeout``: Timeout setting for the action (in seconds)
* ``no_fail``: Boolean value (``True`` or ``False``). If ``True``, no error is
  reported when the expected input is not read
* ``mute``: Boolean value (``True`` or ``False``). If ``True``, the data read is not logged

.. code-block:: yaml
    :caption: matching several values, and with a regular expression

    # succeeds as soon as one of the three strings is received
    - read_until:
        expected: [login:, "Password:", "$ "]
        timeout: 10

    # regex: wait for "version X.Y.Z" with any numbers
    - read_until:
        expected: 'version \d+\.\d+\.\d+'
        regex: True
        timeout: 5

The text read by the ``read_until`` action is stored in the global
variable named ``cn_<test_name>`` (See :ref:`global variables<sec_global_variables>`
for more detail on accessing global variables from test items and scripts).
When a list of values is given, the report also records, under the
``matched`` key, which pattern actually matched.

.. note::

    With ``regex: True``, only the last 64 KiB of received text are
    searched. Older text is not searched again.

In the example above, the global variable ``$(cn_test name in GUI)``
would be created at the end of the step. It contains the data that was read.
