import copy
import unittest

from stock import balances


class StockTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(balances([]), {})

    def test_multiple_products_and_negative_totals(self):
        self.assertEqual(balances([
            {'id': 'a', 'sku': 'tea', 'delta': 3},
            {'id': 'b', 'sku': 'tea', 'delta': -3},
            {'id': 'c', 'sku': 'cup', 'delta': -1},
        ]), {'tea': 0, 'cup': -1})

    def test_exact_retry_counted_once(self):
        event = {'id': 'a', 'sku': 'tea', 'delta': 3}
        self.assertEqual(balances([event, dict(event)]), {'tea': 3})

    def test_conflicting_retry_rejected(self):
        for replacement in ({'id': 'a', 'sku': 'cup', 'delta': 3},
                            {'id': 'a', 'sku': 'tea', 'delta': 4}):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                balances([{'id': 'a', 'sku': 'tea', 'delta': 3}, replacement])

    def test_invalid_fields(self):
        for field, value in [('id', ''), ('id', 1), ('sku', ''), ('sku', None),
                             ('delta', True), ('delta', 1.5), ('delta', '2')]:
            event = {'id': 'a', 'sku': 'tea', 'delta': 3}
            event[field] = value
            with self.subTest(event=event), self.assertRaises(ValueError):
                balances([event])

    def test_missing_fields_and_non_mapping(self):
        for event in ({}, {'id': 'a', 'sku': 'tea'}, None):
            with self.subTest(event=event), self.assertRaises(ValueError):
                balances([event])

    def test_generator_and_no_mutation(self):
        events = [{'id': 'a', 'sku': 'tea', 'delta': 0, 'note': 'ignore'}]
        before = copy.deepcopy(events)
        self.assertEqual(balances(iter(events)), {'tea': 0})
        self.assertEqual(events, before)
