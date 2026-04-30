.. _sec_parallel_item:

**parallel** test item
============================================================

This element is of the following form:

.. code-block:: yaml
    :caption: ``parallel`` test item usage example

    - parallel:
        name: My parallel block
        sync: all
        branches:
          - name: Branch A
            steps:
                - py_func:
                    name: Long operation
                    file: long_op.py
                    func_name: do_work
          - name: Branch B
            wait_for:
                condition: <| "$(ready_flag)" == "True" |>
                timeout: 30
            steps:
                - let:
                    name: Mark done
                    values:
                        - branch_b_done: true

The ``parallel`` element runs several sequences of items concurrently. Each
inner sequence is called a *branch* and runs in its own thread. The parent
test item waits for branches to finish according to the ``sync`` policy.

Attributes
--------------------

* ``branches``: required. A list of branches to execute concurrently. Each
  branch has a ``name`` and a ``steps`` list (same structure as a ``group``
  item). It can also declare a ``wait_for`` precondition (see below).
* ``sync``: optional, defaults to ``all``.

  * ``all``: the parallel item completes when *every* branch has finished.
    The result is ``PASS`` if no branch returned ``FAIL`` (skipped or
    disabled branches are ignored, like in ``group``); otherwise ``FAIL``.
  * ``any``: the parallel item completes as soon as the *first* branch
    finishes. The remaining branches are stopped (their next test items
    are not executed). The result is ``PASS`` if at least one branch
    succeeded.

* ``no_fail``: optional. When ``true``, a ``FAIL`` result is forced to
  ``PASS`` for the parallel item itself (same semantics as for any test
  item). Branches keep their own result.

Branch attributes
--------------------

Each entry of ``branches`` is a dict with the following attributes:

* ``name``: required. The branch name. Used in reports and as a prefix
  in the live log output (each line printed by the branch is prefixed
  with ``[<name>] `` so concurrent branches stay readable).
* ``steps``: required. The list of test items executed sequentially
  inside the branch.
* ``wait_for``: optional. Forces the branch to wait until a condition is
  met before running its steps. If the timeout elapses, the branch
  returns ``FAIL`` (the steps are not run). Sub-attributes:

  * ``condition``: a testium expression evaluated repeatedly (every
    100 ms) until it returns ``True``.
  * ``timeout``: maximum wait, in seconds. Defaults to 30.

Reporting
--------------------

Each branch produces its own row in the SQLite report (with type
``Parallel branch``), in addition to the parent ``Parallel`` row. The
``log`` column of each row contains only the output emitted from that
branch's thread, so logs are never mixed between concurrent branches.

In the live (terminal / GUI) output, lines emitted from a branch are
prefixed with ``[<branch name>] ``. The prefix is not stored in the
SQLite log column.

Notes
--------------------

* A ``sleep`` item inside a branch is interruptible: if another
  ``sync: any`` branch wins the race, slow ``sleep`` items are aborted
  within ~50 ms.
* A ``py_func`` or ``console`` item inside a branch is **not**
  interruptible: a ``sync: any`` stop will only take effect after the
  current item returns. The branch will then skip its remaining steps.
* When a user disables a branch in the GUI tree, the branch returns
  ``SKIP`` instantly without affecting the others (it does *not* win a
  ``sync: any`` race).
