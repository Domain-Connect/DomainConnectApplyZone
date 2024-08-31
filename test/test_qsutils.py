import unittest
from domainconnectzone.qsutil import qs2dict, qsfilter


class TestQs2Dict(unittest.TestCase):
    def test_normal_query_string(self):
        self.assertEqual(qs2dict("a=1&b=2"), {'a': '1', 'b': '2'})

    def test_filtered_query_string(self):
        self.assertEqual(qs2dict("a=1&b=2&c=3", filter_items=['b']), {'a': '1', 'c': '3'})

    def test_empty_query_string(self):
        self.assertEqual(qs2dict(""), {})

    def test_query_string_with_no_equals(self):
        self.assertEqual(qs2dict("a&b=2"), {'b': '2'})

    def test_query_string_with_empty_values(self):
        self.assertEqual(qs2dict("a=&b=2"), {'a': '', 'b': '2'})

    def test_query_string_with_duplicate_keys(self):
        self.assertEqual(qs2dict("a=1&a=2"), {'a': '2'})


class TestQsFilter(unittest.TestCase):
    def test_standard_query_string(self):
        # Test with a standard query string, no filters applied
        self.assertEqual(qsfilter("a=1&b=2&c=3"), "a=1&b=2&c=3")

    def test_filtered_query_string(self):
        # Test with a filter applied, expecting certain keys to be removed
        self.assertEqual(qsfilter("a=1&b=2&c=3", filter_items=['b']), "a=1&c=3")

    def test_empty_query_string(self):
        # Test with an empty query string, expecting an empty result
        self.assertEqual(qsfilter(""), "")

    def test_query_string_with_no_equals(self):
        # Test with a malformed query string (missing '='), expecting original string
        self.assertEqual(qsfilter("a&b=2&c"), "a&b=2&c")

    def test_query_string_with_empty_values(self):
        # Test with a query string having empty values, expecting unchanged string
        self.assertEqual(qsfilter("a=&b=2&c="), "a=&b=2&c=")

    def test_query_string_with_duplicate_keys(self):
        # Test with duplicate keys, expecting the filter to work correctly
        self.assertEqual(qsfilter("a=1&a=2&b=3", filter_items=['a']), "b=3")

    def test_filtering_all_keys(self):
        # Test with all keys being filtered out, expecting an empty result
        self.assertEqual(qsfilter("a=1&b=2", filter_items=['a', 'b']), "")

    def test_nonexistent_filter_items(self):
        # Test with filter items that do not exist in the query string
        self.assertEqual(qsfilter("a=1&b=2", filter_items=['c']), "a=1&b=2")
