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
                expected: Something that will never occurs
                timeout: 5
                no_fail: True
                mute: True
            - close:

Attributes
-----------------------

Beside common test items attributes, console test item has specific attributes:

* ``console_name``: console instance name
* ``write_delay``: optional parameter giving the delay to wait in
  milliseconds between each character sent.
* ``steps``: a sequence of actions to be applied to the console, as listed above.

The console test item steps accept the parameters and configurations defined in the next sections.

All the following actions support the ``name`` attribute. The ``name`` is concatenated with
the step type in the *testium* GUI, and recalled in the test log and reports.

``open`` action
-------------------------

The ``open`` action initializes the console with the attributes defined as described below.
The console instance is then added to the ``console_instances`` entry of the global
variables (cf :ref:`global variables<sec_global_variables>`).

Open step accepts the following attribute:

* ``protocol``: Setting of the console protocol, supported protocol are listed
  in table below
* Other attributes are dependent of the protocol in used and are listed
  in table below

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
    |               | ``ssh_user``           | port of the telnet server of the target.  |
    |               +------------------------+-------------------------------------------+
    |               | ``ssh_pwd``            | Password (optional).                      |
    +---------------+------------------------+-------------------------------------------+
    |``serial``     | ``serial_port``        | Serial port to the target.                |
    |               +------------------------+-------------------------------------------+
    |               | ``serial_baudrate``    | Baud rate of the serial connection.       |
    |               +------------------------+-------------------------------------------+
    |               | ``buffered``           | Optinal boolean parameter. If ``False``,  |
    |               |                        | it forces the                             |
    |               |                        | console to read directly the device.      |
    |               |                        | Default: ``True``.                        |
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

``read_until`` action
----------------------------

The ``read_until`` action is waiting for a string pattern from the console,
its parameter are listed below

* ``expected``: Character string to wait for
* ``timeout``: Timeout setting for the action (in seconds)
* ``no_fail``: Boolean value (``True`` or ``False``) leading to no error reported
  if the expected input is not read
* ``mute``: Boolean value (``True`` or ``False``) does not log any readen data

The text read by the ``read_until`` action is stored in the global
variable named ``cn_<test_name>`` (See :ref:`global variables<sec_global_variables>`
for more detail on accessing global variables from test items and scripts).

In the example above, the global variable ``$(cn_test name in GUI)``
would be created at the end of the step. It would contain the resulting
data of the read.
