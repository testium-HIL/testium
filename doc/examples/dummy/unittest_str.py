import unittest


class TestStringMethods(unittest.TestCase):

    def test_upper(self):
        """upper() turns the string to upper case."""
        self.assertEqual('foo'.upper(), 'FOO')

    def test_isupper(self):
        """isupper() detects an upper-case string."""
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def test_split(self):
        """split() cuts on spaces and rejects a non-string separator."""
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)