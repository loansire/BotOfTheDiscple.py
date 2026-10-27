# -*- coding: utf-8 -*-
"""Lecture des ventes vendor (tri des cases, coût) et filtres positionnels."""
import unittest

from bot.bungie.sales import first_cost_quantity, sorted_keys
from bot.features.ada.constants import ADA_SKIP_LEADING, ADA_SKIP_TRAILING
from bot.features.ada.filtering import filtered_items


def sale(item_hash, qty=None):
    return {"itemHash": item_hash, "costs": [{"quantity": qty}] if qty is not None else []}


class SalesTests(unittest.TestCase):
    def test_sorted_keys_numeric(self):
        self.assertEqual(sorted_keys({"10": {}, "2": {}, "x": {}, "1": {}}), ["x", "1", "2", "10"])

    def test_first_cost_quantity(self):
        self.assertEqual(first_cost_quantity(sale(1, 25)), 25)
        self.assertIsNone(first_cost_quantity(sale(1)))
        self.assertIsNone(first_cost_quantity({"costs": [{"quantity": "x"}]}))


class AdaFilteringTests(unittest.TestCase):
    def test_skips_leading_and_trailing_positions(self):
        n = ADA_SKIP_LEADING + ADA_SKIP_TRAILING + 2
        sales = {str(i * 10): sale(100 + i, i) for i in range(n)}
        kept = filtered_items(sales)
        self.assertEqual([h for h, _ in kept], [100 + i for i in range(ADA_SKIP_LEADING, n - ADA_SKIP_TRAILING)])

    def test_too_few_positions(self):
        n = ADA_SKIP_LEADING + ADA_SKIP_TRAILING
        self.assertEqual(filtered_items({str(i): sale(i) for i in range(n)}), [])


if __name__ == "__main__":
    unittest.main()
