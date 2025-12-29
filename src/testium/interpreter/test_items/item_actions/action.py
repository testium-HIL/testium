from interpreter.test_items.test_item import TestItem, LOG_TEST_START, LOG_TEST_STOP


class TestItemAction(TestItem):
    def __init__(
        self,
        action_name,
        item_type,
        dict_item: dict,
        parent: TestItem,
        status_queue,
        filename="",
    ):
        if dict_item is None:
            dict_item = {}
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._dict_name = self._name
        self._name = (
            action_name + " - " + self._name if self._name != "" else action_name
        )
        self._type = item_type

        self.banner = ""
        self.footer = ""
        if self._dict_name != "":
            self.banner = LOG_TEST_START.format(self._name)
            self.footer = LOG_TEST_STOP.format(self._name)

    def write_banner(self):
        if self.banner != "":
            super().write_banner()

    def write_footer(self):
        if self.banner != "":
            super().write_footer()

    @property
    def token(self):
        return self._parent.actions_token
