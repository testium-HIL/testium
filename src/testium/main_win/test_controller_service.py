from interpreter.utils.test_ctrl import TestSetController


class TestControllerService:
    """Typed interface over TestSetController, decoupling the UI from raw RPC strings."""

    def __init__(self, controller: TestSetController) -> None:
        self._ctrl = controller

    # --- Lifecycle ---

    def stop(self) -> None:
        self._ctrl.control("stop")

    def close(self) -> None:
        self._ctrl.control("close")

    def execute(self) -> None:
        self._ctrl.control("execute")

    def loaded(self, timeout: float = None) -> bool:
        return self._ctrl.control("loaded", timeout=timeout)

    def clear(self) -> None:
        self._ctrl.clear()

    # --- Execution control ---

    def pause(self) -> None:
        self._ctrl.control("pause")

    def cont(self) -> None:
        self._ctrl.control("cont")

    # --- Breakpoints ---

    def add_breakpoint(self, item_id) -> None:
        self._ctrl.control("add_breakpoint", item_id=item_id)

    def del_breakpoint(self, item_id) -> None:
        self._ctrl.control("del_breakpoint", item_id=item_id)

    # --- Tree data ---

    def tree(self) -> dict:
        return self._ctrl.control("tree")

    # --- Item state ---

    def get_enabled_state(self, item_id) -> bool:
        return self._ctrl.control("enabled_state", item_id=item_id)

    def set_enabled_state(self, item_id, state: bool, unitary: bool = False) -> None:
        self._ctrl.control("set_enabled_state", item_id=item_id, enabled_state=state, unitary=unitary)

    def check_uncheck_all(self, checked: bool) -> None:
        self._ctrl.control("check_uncheck_all", checked=checked)

    def get_skipped_state(self, item_id) -> bool:
        return self._ctrl.control("skipped_state", item_id=item_id)

    # --- Configuration ---

    def process_param(self, param: str) -> str:
        return self._ctrl.control("process_param", param=param)

    def set_report(self, rep_path: str, rep_type: str, pattern: list) -> None:
        self._ctrl.control("report", rep_path=rep_path, rep_type=rep_type, pattern=pattern)

    def set_test_outputs(self, outputs: list) -> None:
        self._ctrl.control("set_test_outputs", outputs=outputs)

    def get_gd_vars(self) -> dict:
        return self._ctrl.control("get_gd_vars")

    def set_gd_var(self, name: str, value) -> None:
        self._ctrl.control("set_gd_var", name=name, value=value)

    def del_gd_var(self, name: str) -> None:
        self._ctrl.control("del_gd_var", name=name)
