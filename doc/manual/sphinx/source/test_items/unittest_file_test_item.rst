**unittest_file** test item
============================================================

unittest_file test item allows the execution of unittest test script which
is part of python standard libraries.

The tum file prototype is as followed:

.. code-block:: yaml
    :caption: ``unittest_file`` test item usage example

    - unittest_file:
        name: unitTest test item
        test_file: unitTestScript.py
        test_method:
            - test_1
            - test_2

Attributes
------------------

Beside common test items attributes, unittest test item has specific attribute, some of which being mandatory.

* ``test_file``: it is the name (and eventually path) of the unittest file
  to be processed.
* ``test_method``: it is an optional unittest_file test sub-item. If one or more
  elements are present, the unittest python script file is parsed and only
  the corresponding methods are included in the test tree. Otherwise, all
  the test methods are included in the test tree.

Access to global variables entries
----------------------------------

``unittest`` file tests instances have access to the testium global variables
by using the :ref:`helper's library<sec_python_helper_library>`.

Report value from unittest
----------------------------------

Value can be added to the test report from unitTest test at runtime.

.. code-block:: python
    :caption: example of ``unittest`` test item python function

    from  unittest import (TestCase)

    class DummyTests(TestCase):
        def test_01_report(self):
            self.reported_values['key reported']= 'value_reported'

Console use example with unittest item
-----------------------------------------

Here is an example how to use the console module from python ``unittest``.

.. code-block:: python
    :caption: example of a *testium* console usage from a ``unittest`` python function

    from  unittest import (TestCase)
    import console

    class DummyTests(TestCase):
        @classmethod
        def setUpClass(cls):
            cls.consA0= console.TelnetConsole('cons name','192.168.98.123',7001)
            cls.consA0.open()
            cls.promptA0 = 'test-computer>'

        def test_01_console(self):
            self.consA0.write('config')
            self.assertEqual(self.consA0.read_until(self.promptA0, 10), 0)
            self.consA0.write('lsusb && echo "Done."\n')
            status, read_data = self.consA0.read_until('Done.',
                                                        10, return_data=True)
            self.assertEqual(status, 0)
            if read_data.find('ID 04f2:b684 Chicony Electronics Co.')!=-1:
                index=0

        @classmethod
        def tearDownClass(cls):
            cls.consA0.close()