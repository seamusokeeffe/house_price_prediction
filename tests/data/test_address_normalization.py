import unittest

import pandas as pd

from house_valuation.data.address_normalization import normalize_address


class AddressNormalizationTests(unittest.TestCase):
    def test_whitespace_commas_punctuation_and_uppercase(self):
        result = normalize_address("  12   main rd ,  ranelagh..  ")
        self.assertEqual(result.address_normalized, "12 MAIN ROAD, RANELAGH")
        self.assertEqual(result.address_normalization_status, "normalized")

    def test_apostrophe_and_dash_variants(self):
        result = normalize_address("7 Harold\u2019s Cross \u2013 Dublin")
        self.assertEqual(result.address_normalized, "7 HAROLD'S CROSS - DUBLIN")
        self.assertEqual(result.address_match_text, "7 HAROLD'S CROSS - DUBLIN")

    def test_accented_locality_is_preserved_and_match_text_is_folded(self):
        result = normalize_address("10 Dún Laoghaire")
        self.assertEqual(result.address_normalized, "10 DÚN LAOGHAIRE")
        self.assertEqual(result.address_match_text, "10 DUN LAOGHAIRE")

    def test_house_and_unit_numbers_are_preserved(self):
        result = normalize_address("Apartment 5, 32 Mount Pleasant Square, Ranelagh")
        self.assertEqual(result.address_normalized, "APARTMENT 5, 32 MOUNT PLEASANT SQUARE, RANELAGH")

    def test_missing_punctuation_only_and_too_short_addresses(self):
        self.assertEqual(normalize_address("").address_normalization_status, "missing")
        punctuation = normalize_address(" ... ,,, ")
        self.assertEqual(punctuation.address_normalization_status, "missing")
        self.assertIn("punctuation_only_address", punctuation.address_quality_flags)
        too_short = normalize_address("Ranelagh")
        self.assertEqual(too_short.address_normalization_status, "too_short")
        self.assertIn("too_short_address", too_short.address_quality_flags)

    def test_raw_address_is_preserved_and_normalization_is_idempotent(self):
        raw = "  1 St. John's Rd, Dún Laoghaire  "
        first = normalize_address(raw)
        second = normalize_address(first.address_normalized)
        self.assertEqual(first.raw_address, raw)
        self.assertEqual(second.address_normalized, first.address_normalized)

    def test_pd_na_is_missing(self):
        self.assertEqual(normalize_address(pd.NA).address_normalization_status, "missing")


if __name__ == "__main__":
    unittest.main()
