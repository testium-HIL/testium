import unittest
from time import sleep

def donothing():
    return 0

class DummyTests(unittest.TestCase):
    @unittest.skip("test skipped")
    def test_00_skipped(self):
        ''' Test 00 is skipped
        '''
        sleep(0.5)

    def test_01_pass(self):
        ''' Test 01 is passed and adds a report key
        '''
        self.reported_values['key reported']= 'value_reported'
        sleep(0.5)

    def test_02_pass(self):
        ''' Test 02 is passed and adds a report key
        '''
        self.reported_values['key reported']= 'toto'
        sleep(0.5)

    def test_03_fail(self):
        ''' Test 03 is fail by unittest method
        '''
        sleep(0.5)
        self.fail(msg='Fail message')

    def test_04_disabled(self):
        ''' Test 04 is disabled
        '''
        sleep(0.5)

    def test_05_crash(self):
        ''' Test 05 crashes
        '''
        print(crash)