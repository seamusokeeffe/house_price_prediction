"""Tests for deterministic Checkpoint 4 cleaning and physical output."""

from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

import pandas as pd
import pyarrow as pa

from house_valuation.data.cleaning import (
    EXCLUSION_PRIORITY,
    assess_cleaning,
    validate_checkpoint4_parquet,
    write_checkpoint4_parquet,
)
from house_valuation.data.duplicate_detection import assess_duplicate_like_transactions
from house_valuation.data.multi_property import assess_multi_property_frame, load_multi_property_rules
from house_valuation.data.property_scope import assess_property_scope


def base_row(record_id: str) -> dict:
    """Return one valid synthetic Checkpoint 3-like record.

    Args:
        record_id: Unique record identifier.

    Returns:
        Complete evidence dictionary accepted by all Checkpoint 4 layers.
    """

    return {
        "record_id": record_id,
        "source_row_number": int(record_id.split("-")[-1]) if record_id.split("-")[-1].isdigit() else 1,
        "raw_record_fingerprint": f"fp-{record_id}",
        "raw_address": "1 TEST ROAD, RANELAGH",
        "address_normalized": "1 TEST ROAD, RANELAGH",
        "address_quality_flags": "",
        "transaction_date": date(2024, 1, 1),
        "date_parse_status": "parsed",
        "is_future_transaction": False,
        "sale_price_eur_raw": Decimal("500000.00"),
        "sale_price_eur_adjusted": Decimal("500000.00"),
        "price_parse_status": "parsed",
        "is_full_market_price": True,
        "full_market_price_mapping_status": "mapped_full_market",
        "vat_exclusive_flag": False,
        "vat_mapping_status": "mapped_vat_inclusive",
        "sale_price_adjustment_method": "none",
        "property_description_raw": "Second-Hand Dwelling house /Apartment",
        "property_type": "unknown",
        "property_type_source": "unknown",
        "property_type_quality_flag": "ppr_house_apartment_ambiguous",
        "geo_scope": "inference",
        "geography_match_status": "matched",
        "geography_quality_flags": "",
    }


def fully_assess(frame: pd.DataFrame) -> pd.DataFrame:
    """Run all pure Checkpoint 4 assessment layers.

    Args:
        frame: Synthetic Checkpoint 3-like records.

    Returns:
        Cleaning-assessed records.
    """

    rules = load_multi_property_rules("config/multi_property_rules.csv")
    result = assess_multi_property_frame(frame, rules)
    result = assess_property_scope(result)
    result = assess_duplicate_like_transactions(result)
    return assess_cleaning(result)


class CleaningTests(unittest.TestCase):
    """Verify exclusions, precedence, flags, preservation, and schema."""

    def test_target_date_market_vat_and_new_build_policies(self):
        """Apply target, date, market, VAT, and new-build policies."""

        rows = [base_row(f"row-{number}") for number in range(1, 10)]
        rows[0]["sale_price_eur_adjusted"] = None
        rows[1]["sale_price_eur_adjusted"] = Decimal("0")
        rows[2]["sale_price_eur_adjusted"] = Decimal("-1")
        rows[3]["transaction_date"] = None
        rows[3]["date_parse_status"] = "missing"
        rows[4]["is_future_transaction"] = True
        rows[5]["is_full_market_price"] = False
        rows[5]["full_market_price_mapping_status"] = "mapped_not_full_market"
        rows[6]["is_full_market_price"] = None
        rows[6]["full_market_price_mapping_status"] = "unrecognised"
        rows[7]["vat_exclusive_flag"] = True
        rows[7]["vat_mapping_status"] = "mapped_vat_exclusive"
        rows[7]["sale_price_adjustment_method"] = "provisional_house_vat_13_5_percent"
        rows[7]["is_new_build"] = True
        rows[8]["vat_exclusive_flag"] = None
        rows[8]["vat_mapping_status"] = "missing"
        rows[8]["sale_price_adjustment_method"] = "unresolved_vat_flag"
        result = fully_assess(pd.DataFrame(rows)).set_index("record_id")
        for key in ["row-1", "row-2", "row-3"]:
            self.assertEqual(result.loc[key, "exclusion_reason"], "invalid_target")
        self.assertEqual(result.loc["row-4", "exclusion_reason"], "invalid_date")
        self.assertEqual(result.loc["row-5", "exclusion_reason"], "invalid_date")
        self.assertEqual(result.loc["row-6", "exclusion_reason"], "non_full_market_transaction")
        self.assertEqual(result.loc["row-7", "exclusion_reason"], "unresolved_market_price_status")
        self.assertFalse(result.loc["row-8", "exclude_from_training"])
        self.assertEqual(result.loc["row-9", "exclusion_reason"], "unresolved_vat_treatment")

    def test_geography_property_multi_duplicate_and_review_actions(self):
        """Keep review-only signals separate from auto-exclusions."""

        rows = [base_row(f"case-{number}") for number in range(1, 9)]
        rows[0]["geo_scope"] = "out_of_scope"; rows[0]["geography_match_status"] = "unmatched"
        rows[1]["geo_scope"] = "unknown"; rows[1]["geography_match_status"] = "unmatched"
        rows[2]["geo_scope"] = "unknown"; rows[2]["geography_match_status"] = "ambiguous"
        rows[3]["raw_address"] = rows[3]["address_normalized"] = "APARTMENT 2 TEST COURT, RANELAGH"
        rows[4]["raw_address"] = rows[4]["address_normalized"] = "APARTMENTS 1-10 TEST COURT, RANELAGH"
        rows[5]["raw_address"] = rows[5]["address_normalized"] = "12-14 O'CONNELL STREET, RANELAGH"
        rows[6]["raw_address"] = rows[6]["address_normalized"] = "UNIT 4 TEST COURT, RANELAGH"
        rows[7]["sale_price_eur_adjusted"] = Decimal("100000000.00")
        result = fully_assess(pd.DataFrame(rows)).set_index("record_id")
        expected = {
            "case-1": "out_of_scope_geography",
            "case-2": "unmatched_geography_unresolved",
            "case-3": "ambiguous_geography_unresolved",
            "case-4": "excluded_property_type",
            "case-5": "excluded_property_type",
        }
        for key, reason in expected.items():
            self.assertEqual(result.loc[key, "exclusion_reason"], reason)
        self.assertEqual(result.loc["case-6", "multi_property_action"], "review_only")
        self.assertFalse(result.loc["case-6", "exclude_from_training"])
        self.assertEqual(result.loc["case-7", "property_scope_status"], "review_required")
        self.assertFalse(result.loc["case-7", "exclude_from_training"])
        self.assertFalse(result.loc["case-8", "exclude_from_training"])

    def test_multiple_reasons_priority_flags_and_exact_duplicate(self):
        """Retain every reason while applying approved primary precedence."""

        first = base_row("dup-1")
        second = base_row("dup-2")
        first["raw_record_fingerprint"] = second["raw_record_fingerprint"] = "same-fingerprint"
        first["source_row_number"] = 1
        second["source_row_number"] = 2
        second["is_full_market_price"] = False
        second["full_market_price_mapping_status"] = "mapped_not_full_market"
        result = fully_assess(pd.DataFrame([first, second])).set_index("record_id")
        self.assertEqual(result.loc["dup-1", "duplicate_action"], "retain_representative")
        self.assertEqual(result.loc["dup-2", "duplicate_action"], "auto_exclude")
        self.assertIn("duplicate_unresolved", result.loc["dup-2", "exclusion_reasons"])
        self.assertIn("non_full_market_transaction", result.loc["dup-2", "exclusion_reasons"])
        self.assertEqual(result.loc["dup-2", "exclusion_reason"], "non_full_market_transaction")
        self.assertEqual(EXCLUSION_PRIORITY[0], "invalid_target")
        flags = result.loc["dup-2", "quality_flags"].split("|")
        self.assertEqual(flags, list(dict.fromkeys(flags)))

    def test_schema_readback_preservation_and_determinism(self):
        """Validate explicit schema, read-back, inherited values, and determinism."""

        frame = pd.DataFrame([base_row("schema-1"), base_row("schema-2")])
        first = fully_assess(frame)
        second = fully_assess(frame)
        pd.testing.assert_frame_equal(first, second)
        input_table = pa.Table.from_pandas(frame, preserve_index=False)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint4.parquet"
            write_checkpoint4_parquet(first, input_table.schema, path)
            schema = validate_checkpoint4_parquet(path, input_table)
        self.assertIn("cleaning_assessment_status", schema.names)
        self.assertEqual(len(first), len(frame))
        pd.testing.assert_series_equal(first["record_id"], frame["record_id"])

    def test_no_floor_area_or_checkpoint5_behaviour(self):
        """Confirm cleaning contains no size cutoff or final-output mutation."""

        row = base_row("size-1")
        row["floor_area_sqm"] = 500.0
        result = fully_assess(pd.DataFrame([row]))
        self.assertFalse(result.loc[0, "exclude_from_training"])
        self.assertNotIn("sale_price_eur", result.columns)
        self.assertNotIn("log_sale_price", result.columns)


if __name__ == "__main__":
    unittest.main()
