from runtime.tum_except import (ETUMRuntimeError)

from datetime import datetime
from enum import Enum
import json

class TestValue(Enum):
    SUCCESS =  0
    FAILURE = -1
    NORUN   = -2

    def __str__(self):
        r = ''
        if self == self.SUCCESS:
            r = 'PASS'
        if self == self.FAILURE:
            r = 'FAIL'
        if self == self.NORUN:
            r = 'SKIP'
        return r

class TestResult:
    def __init__(self, test=None, result=None, message=''):

        self.test_name = ''
        self.id = -1
        self.test_id = -1
        self.value = None   # Optional : used to handle values to
                            # be evaluated if success of failure (function item for ex.)

        if test is not None:
            self.test_name = test.name()
            self.test_id = test.id()

        self.__reported_values = {}
        self.set(result, message)

    def set(self, result, message = ''):
        self.test_result = result
        if not (message == ''):
            self.message = message
        else:
            self.message = str(self.test_result)

    @property
    def success(self):
        return TestValue.SUCCESS == self.test_result

    @property
    def test_result(self):
        return self._result

    @test_result.setter
    def test_result(self, result):
        if (isinstance(result, TestValue)) or (result is None):
            self._result = result
        else:
            raise(ETUMRuntimeError('Test result (for reporting) must be a "TestValue" class instance'))

    @property
    def reported(self):
        return self.__reported_values

    @reported.setter
    def reported(self, value):
        self.__reported_values.update(value)

    def reportedJSON(self):
        return json.dumps(self.__reported_values)

    def sendStatus(self, status_queue):
        date_str = str(datetime.now()).split('.')[0].split(' ')[1]
        date_str = '[{}]'.format(date_str)
        status = {'id':self.test_id,
                  'name':self.test_name,
                  'value':self.test_result.value,
                  'message':self.message,
                  'date':date_str}
        if status_queue is not None:
            status_queue.put(status)
        else:
            raise(ETUMRuntimeError("TestResult can't send status. status_queue is 'None'"))

