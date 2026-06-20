import threading
from time import sleep, time

from interpreter.test_items.test_item_container import TestItemContainer
from interpreter.test_items.test_item import test_run
from interpreter.test_items.test_result import TestResult, TestValue
from interpreter.utils.constants import TestItemType as cst
from interpreter.utils.eval import eval_to_boolean
from interpreter.utils.param_decl import Param, ParamSet, LIST, BLOCK, Enum
from runtime.tum_except import ETUMSyntaxError
from runtime.string_queue import StringQueue
from runtime.stdout_redirect import stdio_redir


class TestItemParallelBranch(TestItemContainer):
    """One branch of a parallel item. Runs its children sequentially,
    optionally waiting for a condition before starting."""

    PARAMS = ParamSet(
        Param("wait_for", kind=BLOCK,
              doc="Optional block {condition, timeout} that defers the branch "
                  "start until the condition is truthy (or the timeout elapses)."),
    )

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        super().__init__(cst.TYPE_PARALLEL_BRANCH, dict_item, parent, status_queue, filename=filename)
        self._wait_condition = None
        self._wait_timeout = 30
        if "wait_for" in dict_item:
            wf = dict_item["wait_for"]
            if not isinstance(wf, dict):
                raise ETUMSyntaxError(
                    f"'wait_for' in branch '{self.name()}' must be a dict with 'condition' and optional 'timeout'",
                    self.seqFilename(),
                )
            self._wait_condition = wf.get("condition", None)
            self._wait_timeout = float(wf.get("timeout", 30))

    def _wait_start(self):
        """Block until wait_for condition is True, or timeout. Returns False on timeout."""
        if self._wait_condition is None:
            return True
        deadline = time() + self._wait_timeout
        while time() < deadline:
            if self.isStopped():
                return False
            try:
                c = self._prms.expanse(self._wait_condition)
                if eval_to_boolean(c):
                    return True
            except Exception:
                pass
            sleep(0.1)
        return False

    @test_run
    def execute(self):
        if not self._wait_start():
            self.result.set(
                TestValue.FAILURE,
                f"wait_for timeout ({self._wait_timeout}s): condition '{self._wait_condition}' not met",
            )
            return

        result, stopped = self._run_children_sequentially()

        if stopped:
            if result.test_result == TestValue.FAILURE:
                self.result.set(TestValue.FAILURE, "Branch aborted on failure")
            else:
                self.result.set(TestValue.NORUN, "Branch aborted on user request")
        else:
            self.result.set(result.test_result, "")


class TestItemParallel(TestItemContainer):
    """Runs multiple branches concurrently.

    YAML:
        parallel:
            name: ...
            sync: all       # all (default): wait for every branch
                            # any: stop as soon as one branch finishes
            stop_on_failure: false
            branches:
              - name: Branch A
                wait_for:
                  condition: "'$(ready)' == 'True'"
                  timeout: 30
                steps:
                  - ...
              - name: Branch B
                steps:
                  - ...
    """

    PARAMS = ParamSet(
        Param("branches", kind=LIST, required=True,
              doc="List of branch blocks (each branch holds its own 'steps' "
                  "and optional 'wait_for')."),
        Param("sync", kind=Enum("all", "any"), default="all",
              doc="'all' (default) waits for every branch; 'any' returns as "
                  "soon as the first branch completes."),
    )

    def __init__(self, dict_item, parent=None, status_queue=None, filename=""):
        branches = dict_item.get("branches", [])
        if not branches:
            raise ETUMSyntaxError(
                f"'parallel' item requires at least one branch in 'branches'",
                dict_item.get("seq_filename", ""),
            )
        # Inject a synthetic 'steps' key so load_test_recursively can load branches
        # as TestItemParallelBranch children. The base class' _filter_dict_item
        # drops 'steps'; we also drop 'branches' (overridden below) so the F1
        # panel shows only the parallel's own attributes, not the duplicated
        # tree of branches/steps already displayed in the test tree.
        dict_item["steps"] = [{"parallel_branch": b} for b in branches]

        super().__init__(cst.TYPE_PARALLEL, dict_item, parent, status_queue, filename=filename)
        self._sync = str(dict_item.get("sync", "all")).lower()
        if self._sync not in ("all", "any"):
            raise ETUMSyntaxError(
                f"'sync' must be 'all' or 'any', got '{self._sync}'",
                self.seqFilename(),
            )

    def _filter_dict_item(self, dict_item):
        c = super()._filter_dict_item(dict_item)
        # Keep 'branches' so the F1 panel shows the branch list and their
        # per-branch attributes (name, wait_for, condition, ...), but strip
        # the 'steps' inside each branch — the steps are already visible as
        # children in the test tree and would just duplicate the information.
        if isinstance(c, dict) and isinstance(c.get("branches"), list):
            stripped = []
            for b in c["branches"]:
                if isinstance(b, dict):
                    stripped.append({k: v for k, v in b.items() if k != "steps"})
                else:
                    stripped.append(b)
            c["branches"] = stripped
        return c

    def _stop_branch_recursively(self, item):
        item.stop()
        for i in range(item.childCount()):
            self._stop_branch_recursively(item.child(i))

    @test_run
    def execute(self):
        branch_results = [None] * self.childCount()
        any_done = threading.Event()

        def run_branch(idx):
            branch = self.child(idx)
            stdio_redir.register_thread(buffer=StringQueue(), branch=branch.name())
            try:
                # sync:any: if another branch already won the race, mark this
                # branch as stopped so its execute() skips children but still
                # goes through the normal addTest path (clean DB entry).
                if self._sync == "any" and any_done.is_set():
                    branch.stop()
                try:
                    result = branch.execute()
                except Exception as e:
                    import traceback
                    print(f"[parallel] Branch '{branch.name()}' crashed: {e}")
                    traceback.print_exc()
                    branch.result.set(TestValue.FAILURE, f"Branch crashed: {e}")
                    result = branch.result
                branch_results[idx] = result
                # Only a branch that actually ran (SUCCESS or FAILURE) wins the
                # sync:any race. A disabled or skipped branch returns NORUN
                # almost instantly and must not stop legitimate branches.
                if self._sync == "any" and result.test_result != TestValue.NORUN:
                    any_done.set()
                    for j in range(self.childCount()):
                        if j != idx:
                            self._stop_branch_recursively(self.child(j))
            finally:
                stdio_redir.unregister_thread()

        threads = [
            threading.Thread(target=run_branch, args=(i,), daemon=True)
            for i in range(self.childCount())
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if self._sync == "all":
            # Pass if no branch failed; disabled/skipped branches (NORUN) are
            # ignored, matching how Group/Cycle treat disabled children.
            success = all(
                r is not None and r.test_result != TestValue.FAILURE
                for r in branch_results
            )
        else:
            # Pass if at least one branch ran and succeeded.
            success = any(
                r is not None and r.test_result == TestValue.SUCCESS
                for r in branch_results
            )

        self.result.set(
            TestValue.SUCCESS if success else TestValue.FAILURE,
            f"parallel sync={self._sync}",
        )
