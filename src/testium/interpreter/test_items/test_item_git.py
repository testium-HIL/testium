from interpreter.test_items.test_item import (TestItem, test_run)
from interpreter.test_items.test_result import (TestValue)
from interpreter.utils.constants import TestItemType as cst
from runtime.tum_except import ETUMParamError, ETUMSyntaxError
import interpreter.utils.version as git

class TestItemGit(TestItem):
    """
    This item expect only one parameter which is a string or list of string being the path to the git folder
    """
    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_GIT.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self._type = cst.TYPE_GIT
        self.is_container = False
        self.repo = self._prms.getParamAll('repo',  processed=True, required=True)

    @test_run
    def execute(self):
        ret=''
        if isinstance(self.repo[0], str):
            repo = self._prms.expanse(self.repo[0])
            ret = git.get_version(repo)
        elif isinstance(self.repo, list):
            for r in self.repo:
                repo = self._prms.expanse(r)
                ret += git.get_version(repo) + '\n'
        else:
            ETUMSyntaxError(f"The '{self.cmd()}' test item named '{self.name()}' expected a string or list but has '{self.repo}'",
                            self.seqFilename())

        if "Warning" in ret:
            res = TestValue.FAILURE
        else:
            res = TestValue.SUCCESS

        self.result.set(res, ret)
