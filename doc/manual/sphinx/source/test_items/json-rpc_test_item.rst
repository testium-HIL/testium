.. _sec_jsonrpc_test_item:

**jsonrpc** test item
============================================================

The `jsonrpc` test item is used to access jsonrpc servers, by sending queries and analysing the
answers.
It supports JSONRPC `v1.0 <https://www.jsonrpc.org/specification_v1>`_ or
`v2.0 <https://www.jsonrpc.org/specification>`_.

This test item can access the jsonrpc server by using an existing
:ref:`console<sec_console_test_item>` or directly using a UDP protocol.
Two low level *adapters* can be then chosen: ``udp`` or ``console``.

Example of ``jsonrpc`` test item with the console adapter:

.. code-block:: yaml
    :caption: ``json_rpc`` test item usage example

    - json_rpc:
        name: JSONRPC console Query
        doc: JSONRPC console Query not waiting (only send)
        console:
          name : jsonrpc_server
          prompt: "@@>"
        timeout: 1
        version: "2.0"
        steps:
            - query:
                method: echo
                params:
                    a: Hello world
                    b: [0, 1, 2, 3]
                id: 3095372
                no_wait: True

    - [...]

    - json_rpc:
        name: JSONRPC console Reception
        doc: JSONRPC console reception of the previous request
        console: {name : jsonrpc_server}
        timeout: 1
        steps:
            - receive:
                name: console reception
                id: 3095372
                timeout: 0.5

Attributes
-----------------------

the jsonrpc attributes are:

* ``timeout``: global communication timeout in seconds. It is a floating point number.
* ``version``: "1.0" or "2.0" (as a string) depending on the version of the JSONRPC
  standard which is supported.
* ``mute``: a boolean giving the verbosity of the jsonrpc exchanges on the log output.
* An :ref:`Adapter<sec_jsonrpc_adapters>` is to be chosen between:

  * Console,
  * UDP,
* ``steps``: a sequence of actions as described in the sections below.

.. _sec_jsonrpc_adapters:

Steps
-----------------------

the jsonrpc steps can be of the following:

* ``open``: used by UDP to open the socket explicitely,
* ``close``: used by UDP adapter to close the socket explicitely,
* ``query``: performs a complete or partial JSONRPC call,
* ``receive``: used to receive the JSONRPC result of call previously
  done by the ``query`` action.

If no ``expected_value`` attribute is defined for ``query`` or ``receive`` actions,
the success of the step will depend on the value returned by the JSONRPC frame.
Indeed, this protocol defines a mean to notify if the remote procedure has succeeded
or failed.

All the actions support the ``name`` attribute. The ``name`` is concatenated with
the action type in the *testium* GUI, and recalled in the test log and reports.

adapter attributes
^^^^^^^^^^^^^^^^^^^^^^

The adapters attributes are listed in the table below.

.. flat-table:: jsonrpc adapters
   :header-rows: 2
   :stub-columns: 1
   :widths: 10 20 15 10 10 10

   * - :rspan:`1` adapter
     - :cspan:`2` attribute
     - :cspan:`1` Description

   * - attribute
     - *type*

   * - :rspan:`2` Console
     - ``console``
     - *dictionary*
     - The console adapter configuration

   * - ``console.name``
     - *string*
     - The name of the console which will be retrieved from
       the :ref:`global variables<sec_global_variables>`. See also
       the :ref:`console test item<sec_console_test_item>`.

   * - ``console.prompt``
     - *string*
     - the eventual enclosing suffix of the jsonrpc frame.

   * - :rspan:`5` UDP
     - ``udp``
     - *dictionary*
     - The UDP adapter configuration

   * - ``udp.server``
     - *string*
     - UDP server hostname or IP address. A multicast address
       (224.0.0.0/4) enables the multicast mode (see below).

   * - ``udp.snd_port``
     - *integer*
     - UDP server listening port

   * - ``udp.rcv_port``
     - *integer*
     - UDP answer reception port (on client side)

   * - ``udp.bufsize``
     - *integer*
     - the maximum expected size of the buffer received while waiting for
       a jsonrpc frame.

   * - ``udp.multicast_if``
     - *string*
     - multicast mode only: IP address of the local interface used to send
       to and join the group (default: the kernel default interface).

Multicast
^^^^^^^^^^^^^^^^^^^^^^

When ``udp.server`` is a multicast group address (224.0.0.0/4), the ``open``
action sends the requests to the group and joins it on the reception socket.

The response scheme is decided by the *server*, not by *testium*; no client
configuration is needed, both are received transparently on ``udp.rcv_port``:

* the server answers in unicast to the source address of the request
  (the usual case): received because the socket is bound to ``rcv_port``,
* the server answers to the multicast group itself (discovery-style
  protocols): received because ``open`` joined the group. The server must
  then address the group on the client reception port.

Use ``udp.multicast_if`` to pin the exchanges to a given local interface
(e.g. ``127.0.0.1`` for a same-host test bench); otherwise the kernel routing
decides which interface carries the multicast traffic — on a multi-homed
host the request may leave through the wrong network.

.. warning::
   The UDP socket is created once by the ``open`` action and shared, through
   ``rcv_port``, by every later ``query``/``receive`` item. ``multicast_if``
   only acts at socket creation: set it on the item holding the ``open``
   action. On any other item it is ignored (a warning is logged).

``open`` action
-------------------------

The ``open`` jsonrpc action is only used with the
`UDP adapter<sec_jsonrpc_adapters>` but is mandatory before any ``query`` action.

No parameter is required.

``close`` action
---------------------------

The ``close`` jsonrpc action is only used with the
`UDP adapter<sec_jsonrpc_adapters>` but is mandatory after JSONRPC transfers are finished.

No parameter is required.

``query`` action
---------------------------

The ``query`` jsonrpc action has the following attributes:

* ``method``: JSONRPC method to be called,
* ``params``: JSONRPC param (must be conforming to the version defined above), by default it is an empty list.
* ``id``: JSONRPC id. If not defined or starts with ``rand``, it is chosen randomly.
  Otherwise it must be an integer value,
* ``timeout``: reception timeout in seconds. It is a floating point number.
  It is by default the jsonrpc timeout.
* ``no_wait``: Optional boolean. False by default. This attribute defines if
  the reception is performed in this step (reception can be done appart, in the
  ``receive`` action described below),

``receive`` action
---------------------------

The ``receive`` jsonrpc action has the following attributes:

* ``id``: JSONRPC id as an integer value,
* ``timeout``: reception timeout in seconds. It is a floating point number,
  It is by default the jsonrpc timeout.
