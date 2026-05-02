import os
import sys
from unittest import (TestCase, TestSuite, TextTestRunner,
    TextTestResult)
from unittest.loader import defaultTestLoader

import api.testium as tm
from runtime.tum_except import (ETUMFileError)
from interpreter.utils.modules import load_source
from interpreter.test_items.test_item import (TestItem, test_run, LOG_TEST_STOP, LOG_TEST_START)
from interpreter.test_items.test_result import (TestResult, TestValue)
from interpreter.test_items.test_item import test_data
from interpreter.utils.constants import TestItemType as cst
from runtime.stdout_redirect import stdio_redir

class UnittestResult(TextTestResult):
    """Test result adapted for unittest test"""
    _status_queue = None
    reported_values = {}

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stdio_redir.stream, descriptions, verbosity)
        self.separator2 = ""

    @classmethod
    def setStatusQueue(self, status_queue):
        self._status_queue = status_queue

    def __sendStatus(self, test, result, msg=''):
        if hasattr(test, '_id'):
            self.res = TestResult(result=result, message = msg)
            self.res.test_id = test._id
            self.res.sendStatus(self._status_queue)
            self.duration = tm.timestamp() - self._timestamp

    def __sendStatusStarted(self, test):
        self._status_queue.put({'id':test._id, 'status':'started',
                                'timestamp':self._timestamp})

    def __sendStatusStopped(self, test):
        self._status_queue.put({'id':test._id, 'status':'finished', 'duration': self.duration})

    def stop(self):
        super().stop()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.__sendStatus(test, TestValue.SUCCESS)

    def addError(self, test, err):
        super().addError(test, err)
        self.__sendStatus(test, TestValue.FAILURE, str(err[1]))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.__sendStatus(test, TestValue.FAILURE, str(err[1]))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.__sendStatus(test, TestValue.NORUN)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.__sendStatus(test, TestValue.FAILURE, str(err[1]))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.__sendStatus(test, TestValue.SUCCESS)

    def startTest(self, test):
        """Called when the given test is about to be run.
        """
        self._timestamp = test.t0
        s = LOG_TEST_START.format(test._item_name)
        s = (s + '{:>'+str(max(1, 80-len(s))) +
                 '}').format(str('@@{}@@'.format(test.t0)))
        print(s)
        self.__sendStatusStarted(test)
        super().startTest(test)

    def stopTest(self, test):
        "Called when the given test is about to be run"
        super().stopTest(test)
        print(LOG_TEST_STOP.format(test._item_name) + ": " + str(self.res.test_result))
        self.__sendStatusStopped(test)

class TestItemUnittestElement(TestItem):
    def __init__(self, name, parent = None, status_queue=None, filename=""):
        super().__init__(None, parent, status_queue, filename=filename)
        self.is_container = False
        self._name = name
        self._type = cst.TYPE_UNITTEST_STEP
        self.banner = ""
        self.footer = ""


class TestItemUnittestFile(TestItem):
    def __init__(self, dict_item, parent = None, status_queue=None, filename=""):
        self._name = cst.TYPE_UNITTEST.item_name
        super().__init__(dict_item, parent, status_queue, filename=filename)
        self.is_container = True
        self._type = cst.TYPE_UNITTEST
        self._fileName = self._prms.getParam('test_file', required = True, processed = True)
        self._testDir = ''
        self._test_methods = self._prms.getParamAll('test_method', processed=True)

    def setTestDir(self, dir):
        self._testDir=dir

    def __runALoop(self):
        results = []
        i = 0
        to_be_stopped = False
        while (not self.isStopped()) and (i < self.childCount()) and (not to_be_stopped):
            if not self.child(i).enabled:
                res = TestResult(self.child(i), TestValue.NORUN)
            else:
                ts = TestSuite()
                test = self.child(i).test
                test.t0 = tm.timestamp()
                test._item_name = self.child(i).name()
                ts.addTest(test)
                self.child(i).t0 = test.t0
                try:
                    try:
                        result = self.test_runner.run(ts)
                    finally:
                        self.child(i).duration = tm.timestamp() - self.child(i).t0
                except:
                    res = TestResult(self.child(i), TestValue.FAILURE, '"{}" crashed.'.format(test._item_name))
                else:
                    if len(result.failures)>0 or len(result.errors)>0:
                        res = TestResult(self.child(i), TestValue.FAILURE)
                    elif (len(result.skipped)>0):
                        res = TestResult(self.child(i), TestValue.NORUN)
                    else:
                        res = TestResult(self.child(i), TestValue.SUCCESS)
                self.report.addTest(self.child(i), res)
                if res.test_result == TestValue.FAILURE and self._stop_on_failure:
                    to_be_stopped = True
            results.append(res)
            i = i + 1

        test_success = TestValue.SUCCESS
        for res in results:
            if res.test_result == TestValue.FAILURE:
                test_success = TestValue.FAILURE
                break

        result = TestResult(None, test_success, 'Unittest file')
        return result

    @test_run
    def execute(self):
        # set the queue where steps have to send their results
        self.test_runner.resultclass.setStatusQueue(self.status_queue)

        # Execute the tests
        result = self.__runALoop()

        if self.isStopped():
            self.result.set(TestValue.NORUN, 'Group execution aborted on user request')
        else:
            self.result.set(result.test_result, 'unittest ' + str(result.test_result))

    def load(self):
        ret = {}
        if self._fileName == '':
            raise ETUMFileError('A file name is expected but got "None"')

        if not os.path.isabs(self._fileName):
            self._fileName = os.path.normpath(os.path.join(self._testDir, self._fileName))

        if not os.path.isfile(self._fileName):
            raise ETUMFileError('File "%s" is not found' % (self._fileName))

        sys.path.append(os.path.dirname(self._fileName))

        self.test_runner = TextTestRunner(verbosity=2,
                                          resultclass=UnittestResult,
                                          failfast=self._stop_on_failure)
        self.test_loader = defaultTestLoader

        test_suites = []
        modulename = os.path.basename(self._fileName).split('.')[0]
        module = load_source(modulename, os.path.abspath(self._fileName))
        testnames = []
        for name in dir(module):
            try:
                obj = getattr(module, name)
                if (isinstance(obj, type) and issubclass(obj, TestCase)):
                    tcn = self.test_loader.getTestCaseNames(obj)
                    testnames = [*testnames, *tcn]
                    test_suites.append(TestSuite(list(map(obj, tcn))))
            except ImportError:
                # case where the module in scope can't be imported for any reason
                pass

        for test_method in self._test_methods:
            if not test_method in testnames:
                raise ETUMFileError('Test method "%s" is not found in "%s"' % (
                    test_method, self._fileName))

        for tests in test_suites:
            for test in tests:
                test_name = (str(test).split('(')[0]).strip()
                if (test_name in self._test_methods) or (len(self._test_methods) == 0):
                    item = TestItemUnittestElement(test_name, self)
                    # set the test_item id in the test_step instance for
                    # later status sending
                    test._id = item.id()
                    test.reported_values = {}
                    item.test = test
                    item._doc = test._testMethodDoc
                    if item._doc is None:
                        item._doc = ''

                    ret.update(test_data(item, {}))

        return ret