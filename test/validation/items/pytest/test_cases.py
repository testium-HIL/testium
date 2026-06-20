import pytest


def test_01_pass():
    ''' Test 01 passes '''
    assert 1 + 1 == 2


def test_02_pass():
    ''' Test 02 passes '''
    assert "a" in "abc"


def test_03_fail():
    ''' Test 03 fails on purpose '''
    assert 1 == 2, "deliberate failure"


@pytest.mark.skip(reason="skipped on purpose")
def test_04_skip():
    ''' Test 04 is skipped '''
    assert False


@pytest.mark.parametrize("n", [1, 2])
def test_05_param(n):
    ''' Test 05 is parametrised, both cases pass '''
    assert n < 3
