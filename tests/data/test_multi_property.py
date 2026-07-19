"""Tests for transparent Checkpoint 4 multi-property rules."""

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from house_valuation.data.multi_property import (
    MultiPropertyConfigError,
    assess_multi_property_frame,
    load_multi_property_rules,
)


CONFIG = Path("config/multi_property_rules.csv")


class MultiPropertyTests(unittest.TestCase):
    """Exercise matches, boundaries, aggregation, and invalid configuration."""

    @classmethod
    def setUpClass(cls):
        """Load reviewed rules once for the test class."""

        cls.rules = load_multi_property_rules(CONFIG)

    def assess(self, addresses):
        """Assess a sequence of normalised addresses."""

        return assess_multi_property_frame(pd.DataFrame({"address_normalized": addresses}), self.rules)

    def test_high_precision_matches_and_boundaries(self):
        """Match every approved high-precision rule family."""

        rows = self.assess([
            "APARTMENTS 1-12, TEST COURT",                     # MP001
            "APT 1 2 3, TEST COURT",                           # MP002
            "30 APTS AND ONE COMMERCIAL UNIT, TEST COURT",     # MP003
            "BLOCK 8A AND BLOCK 8B, TEST COURT",               # MP004
            "8 PEMBROKE ROAD & 8 BAGGOT LANE, BALLSBRIDGE",    # MP005
            "1-6 INCLUSIVE, THE MEADOWS",                      # MP006
            "ENTIRE BLOCK, TEST COURT",                        # MP007
        ])
        for index, rule_id in enumerate(["MP001", "MP002", "MP003", "MP004", "MP005", "MP006", "MP007"]):
            self.assertIn(rule_id, rows.loc[index, "multi_property_rule_ids"])
            self.assertEqual(rows.loc[index, "multi_property_action"], "auto_exclude")
            self.assertEqual(rows.loc[index, "single_dwelling_confidence"], "low")

    def test_review_only_signals_and_false_positives(self):
        """Keep medium evidence review-only and reject punctuation shortcuts."""

        rows = self.assess([
            "APT 7 ARRANMORE, 13-17 PEMBROKE ROAD",             # generic building range
            "APARTMENT 3-10, TEST COURT",                      # ambiguous singular range
            "7 OLDWOOD PHASE 11, ROSCOMMON",                   # individual phase dwelling
            "12-14 O'CONNELL-STREET",                          # ordinary ranged building
            "6 SCRAHAN PLACE; KILLARNEY",                      # semicolon typo
            "12 MAIN STREET, DUBLIN",                          # comma-separated single address
            "NO 4 TEST DEVELOPMENT",                           # development alone is review
        ])
        self.assertEqual(rows.loc[0, "multi_property_action"], "review_only")
        self.assertEqual(rows.loc[1, "multi_property_action"], "review_only")
        self.assertEqual(rows.loc[2, "multi_property_action"], "review_only")
        self.assertEqual(rows.loc[3, "multi_property_action"], "review_only")
        self.assertEqual(rows.loc[4, "multi_property_action"], "none")
        self.assertEqual(rows.loc[5, "multi_property_action"], "none")
        self.assertEqual(rows.loc[6, "multi_property_action"], "review_only")

    def test_price_vat_and_new_build_are_not_rule_inputs(self):
        """Prove price, VAT, and new-build status cannot trigger a rule."""

        frame = pd.DataFrame({
            "address_normalized": ["1 ORDINARY ROAD", "2 ORDINARY ROAD", "3 ORDINARY ROAD"],
            "sale_price_eur_adjusted": [100_000_000, 200_000, 200_000],
            "vat_exclusive_flag": [False, True, False],
            "is_new_build": [False, False, True],
        })
        result = assess_multi_property_frame(frame, self.rules)
        self.assertTrue(result["multi_property_action"].eq("none").all())

    def test_multiple_hits_are_stable_and_auto_exclude_wins(self):
        """Retain all hits in stable order and apply action precedence."""

        result = self.assess(["30 APARTMENTS 1-30 INCLUSIVE, BLOCK A AND BLOCK B"])
        ids = result.loc[0, "multi_property_rule_ids"].split("|")
        self.assertEqual(ids, sorted(ids))
        self.assertGreaterEqual(len(ids), 3)
        self.assertEqual(result.loc[0, "multi_property_max_severity"], "high")
        self.assertEqual(result.loc[0, "multi_property_action"], "auto_exclude")

    def test_invalid_configuration_fails_clearly(self):
        """Reject unknown matchers and malformed rule metadata."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.csv"
            path.write_text(
                "rule_id,description,matcher,pattern,severity,action,rationale,false_positive_risk\n"
                "BAD,bad,unknown,[,high,auto_exclude,bad,bad\n",
                encoding="utf-8",
            )
            with self.assertRaises(MultiPropertyConfigError):
                load_multi_property_rules(path)


if __name__ == "__main__":
    unittest.main()
