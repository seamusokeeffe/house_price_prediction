"""Tests for deterministic duplicate-like transaction assessment."""

from datetime import date
from decimal import Decimal
import unittest

import pandas as pd

from house_valuation.data.duplicate_detection import assess_duplicate_like_transactions


def duplicate_fixture() -> pd.DataFrame:
    """Return synthetic exact, plausible, weak, and distinct transactions."""

    rows = []
    def add(record_id, source_row, fingerprint, raw_address, normalized, day, price, full=True, vat=False, description="Second"):
        """Append one compact duplicate fixture row."""

        rows.append({
            "record_id": record_id, "source_row_number": source_row,
            "raw_record_fingerprint": fingerprint, "raw_address": raw_address,
            "address_normalized": normalized, "transaction_date": day,
            "sale_price_eur_raw": Decimal(price), "sale_price_eur_adjusted": Decimal(price),
            "is_full_market_price": full, "vat_exclusive_flag": vat,
            "property_description_raw": description,
        })
    add("exact-later", 20, "fp-exact", "1 Road", "1 ROAD", date(2024, 1, 1), "100.00")
    add("exact-first", 10, "fp-exact", "1 Road", "1 ROAD", date(2024, 1, 1), "100.00")
    add("plausible-a", 30, "fp-a", "2 Road", "2 ROAD", date(2024, 2, 1), "200.00")
    add("plausible-b", 31, "fp-b", "2 ROAD", "2 ROAD", date(2024, 2, 1), "200.00")
    add("weak-a", 40, "fp-c", "3 Road", "3 ROAD", date(2024, 3, 1), "300.00", True)
    add("weak-b", 41, "fp-d", "3 Road", "3 ROAD", date(2024, 3, 1), "300.00", False)
    add("distinct-a", 50, "fp-e", "4 Road", "4 ROAD", date(2024, 4, 1), "400.00")
    add("distinct-b", 51, "fp-f", "5 Road", "5 ROAD", date(2024, 4, 1), "400.00")
    add("repeat-date", 60, "fp-g", "4 Road", "4 ROAD", date(2024, 5, 1), "500.00")
    return pd.DataFrame(rows)


class DuplicateDetectionTests(unittest.TestCase):
    """Verify categories, stable groups, representatives, and preservation."""

    def test_categories_representative_and_no_row_removal(self):
        """Classify all categories and retain a deterministic exact representative."""

        frame = duplicate_fixture()
        result = assess_duplicate_like_transactions(frame)
        self.assertEqual(len(result), len(frame))
        exact = result[result["raw_record_fingerprint"] == "fp-exact"]
        self.assertTrue(exact["duplicate_group_id"].nunique() == 1)
        self.assertTrue(exact["duplicate_representative_record_id"].eq("exact-first").all())
        self.assertEqual(result.set_index("record_id").loc["exact-first", "duplicate_action"], "retain_representative")
        self.assertEqual(result.set_index("record_id").loc["exact-later", "duplicate_action"], "auto_exclude")
        self.assertEqual(result.set_index("record_id").loc["plausible-a", "duplicate_status"], "plausible_duplicate_publication")
        self.assertEqual(result.set_index("record_id").loc["weak-a", "duplicate_status"], "unresolved_duplicate_like")
        self.assertEqual(result.set_index("record_id").loc["distinct-a", "duplicate_status"], "same_day_distinct_transaction")
        self.assertEqual(result.set_index("record_id").loc["repeat-date", "duplicate_status"], "not_duplicate_like")

    def test_group_ids_are_invariant_to_row_order(self):
        """Keep content-derived group identifiers invariant to input ordering."""

        frame = duplicate_fixture()
        first = assess_duplicate_like_transactions(frame).set_index("record_id")["duplicate_group_id"].sort_index()
        second = assess_duplicate_like_transactions(frame.sample(frac=1, random_state=7)).set_index("record_id")["duplicate_group_id"].sort_index()
        pd.testing.assert_series_equal(first, second)


if __name__ == "__main__":
    unittest.main()
