import csv
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from house_valuation.data.filters import filter_training_rows
from house_valuation.data.ppr_ingestion import (
    CONFIRMED_IRISH_AND_MOJIBAKE_PROPERTY_DESCRIPTIONS,
    PPR_ENCODING,
    PRICE_SOURCE_COLUMN,
    PPRPhysicalSchemaError,
    PPRSourceConfig,
    PPRSourceSchemaError,
    REQUIRED_SOURCE_COLUMNS,
    build_ppr_source_standardised,
    build_ppr_source_standardised_result,
    checkpoint2_arrow_schema,
    map_property_description,
    read_source_header,
    validate_checkpoint2_parquet,
    validate_source_columns,
    write_checkpoint2_parquet,
)
from house_valuation.models.baseline import GroupedMedianBaseline


class PPRIngestionTests(unittest.TestCase):
    def test_cp1252_decoding_and_explicit_decoding_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ppr.csv"
            self.write_fixture(path, rows=[self.row(price="\u20ac1,000.00")], encoding=PPR_ENCODING)

            header = read_source_header(path, encoding=PPR_ENCODING)
            self.assertIn(PRICE_SOURCE_COLUMN, header)

            with self.assertRaises(UnicodeDecodeError):
                read_source_header(path, encoding="utf-8")

    def test_required_columns_can_appear_in_different_order(self):
        columns = list(reversed(REQUIRED_SOURCE_COLUMNS))
        validation = validate_source_columns(columns)
        self.assertEqual(validation.missing_columns, [])

    def test_full_ingestion_required_columns_reordered(self):
        frame = self.transform(
            [self.row(address="1 Reordered Road")],
            fieldnames=list(reversed(REQUIRED_SOURCE_COLUMNS)),
        )
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.loc[0, "raw_address"], "1 Reordered Road")

    def test_missing_required_source_column_fails(self):
        columns = [column for column in REQUIRED_SOURCE_COLUMNS if column != "Address"]
        with self.assertRaises(PPRSourceSchemaError):
            validate_source_columns(columns)

    def test_unexpected_additional_source_column_is_reported(self):
        validation = validate_source_columns(REQUIRED_SOURCE_COLUMNS + ["Extra Column"])
        self.assertEqual(validation.unexpected_columns, ["Extra Column"])

        frame, validation, _ = self.transform_with_validation(
            [self.row(address="1 Extra Road", extra={"Extra Column": "kept"})],
            fieldnames=REQUIRED_SOURCE_COLUMNS + ["Extra Column"],
        )
        self.assertEqual(len(frame), 1)
        self.assertEqual(validation.unexpected_columns, ["Extra Column"])
        self.assertIn("source_raw__extra_column", frame.columns)
        self.assertEqual(frame.loc[0, "source_raw__extra_column"], "kept")

    def test_duplicate_source_column_names_fail(self):
        with self.assertRaises(PPRSourceSchemaError):
            validate_source_columns(REQUIRED_SOURCE_COLUMNS + ["Address"])

    def test_preserved_raw_column_name_collision_fails(self):
        with self.assertRaisesRegex(PPRSourceSchemaError, "Preserved raw source column-name collisions"):
            validate_source_columns(REQUIRED_SOURCE_COLUMNS + ["Extra Column", "Extra-Column"])

    def test_date_price_status_vat_and_fingerprints(self):
        rows = [
            self.row(date_text="31/12/2024", price="\u20ac1,000.00", vat="No", full_market="No"),
            self.row(date_text="31/12/2024", price="\u20ac1,000.00", vat="No", full_market="No"),
            self.row(date_text="01/02/2024", price="\u20ac100.00", vat="Yes", full_market="Yes"),
            self.row(date_text="2024-02-01", price="not money", vat="Maybe", full_market="Maybe"),
            self.row(date_text="22/06/2026", price="\u20ac0.00", vat="", full_market=""),
            self.row(date_text="01/01/2024", price="\u20ac-1.00", vat="No", full_market="No"),
        ]
        frame = self.transform(rows)

        self.assertEqual(frame.loc[0, "transaction_date"], date(2024, 12, 31))
        self.assertEqual(frame.loc[3, "date_parse_status"], "invalid")
        self.assertTrue(frame.loc[4, "is_future_transaction"])

        self.assertEqual(frame.loc[0, "sale_price_eur_raw"], Decimal("1000.00"))
        self.assertEqual(frame.loc[3, "price_parse_status"], "invalid")
        self.assertEqual(frame.loc[4, "price_parse_status"], "non_positive")
        self.assertEqual(frame.loc[5, "price_parse_status"], "non_positive")

        self.assertTrue(frame.loc[0, "is_full_market_price"])
        self.assertFalse(frame.loc[2, "is_full_market_price"])
        self.assertEqual(frame.loc[3, "full_market_price_mapping_status"], "unrecognised")
        self.assertEqual(frame.loc[4, "full_market_price_mapping_status"], "missing")

        self.assertFalse(frame.loc[0, "vat_exclusive_flag"])
        self.assertEqual(frame.loc[0, "sale_price_eur_adjusted"], Decimal("1000.00"))
        self.assertEqual(frame.loc[0, "sale_price_adjustment_method"], "none")
        self.assertTrue(frame.loc[2, "vat_exclusive_flag"])
        self.assertEqual(frame.loc[2, "vat_rate_applied"], Decimal("0.135"))
        self.assertEqual(frame.loc[2, "sale_price_eur_adjusted"], Decimal("113.50"))
        self.assertEqual(frame.loc[2, "sale_price_adjustment_method"], "provisional_house_vat_13_5_percent")
        self.assertEqual(frame.loc[3, "vat_mapping_status"], "unrecognised")
        self.assertEqual(frame.loc[4, "vat_mapping_status"], "missing")

        self.assertNotEqual(frame.loc[0, "record_id"], frame.loc[1, "record_id"])
        self.assertEqual(frame.loc[0, "raw_record_fingerprint"], frame.loc[1, "raw_record_fingerprint"])
        self.assertIn("source_raw__address", frame.columns)

    def test_missing_date_and_missing_price(self):
        frame = self.transform([self.row(date_text="", price="")])
        self.assertEqual(frame.loc[0, "date_parse_status"], "missing")
        self.assertTrue(pd.isna(frame.loc[0, "transaction_date"]))
        self.assertEqual(frame.loc[0, "price_parse_status"], "missing")
        self.assertTrue(pd.isna(frame.loc[0, "sale_price_eur_raw"]))
        self.assertEqual(frame.loc[0, "sale_price_adjustment_method"], "invalid_raw_price")

    def test_raw_versus_adjusted_price_preservation(self):
        frame = self.transform([self.row(price="\u20ac100.00", vat="Yes")])
        self.assertEqual(frame.loc[0, "sale_price_eur_raw_text"], "\u20ac100.00")
        self.assertEqual(frame.loc[0, "sale_price_eur_raw"], Decimal("100.00"))
        self.assertEqual(frame.loc[0, "sale_price_eur_adjusted"], Decimal("113.50"))

    def test_documented_vat_rounding_half_up_exact_half_cent(self):
        frame = self.transform([self.row(price="\u20ac0.10", vat="Yes")])
        self.assertEqual(frame.loc[0, "sale_price_eur_adjusted"], Decimal("0.11"))

    def test_configurable_vat_rate_is_used(self):
        frame = self.transform([self.row(price="\u20ac100.00", vat="Yes")], house_vat_rate=Decimal("0.200"))
        self.assertEqual(frame.loc[0, "vat_rate_applied"], Decimal("0.200"))
        self.assertEqual(frame.loc[0, "sale_price_eur_adjusted"], Decimal("120.00"))

    def test_source_column_order_invariant_fingerprints(self):
        row = self.row(address="Order Invariant")
        normal = self.transform([row], fieldnames=REQUIRED_SOURCE_COLUMNS)
        reordered = self.transform([row], fieldnames=list(reversed(REQUIRED_SOURCE_COLUMNS)))
        self.assertEqual(normal.loc[0, "raw_record_fingerprint"], reordered.loc[0, "raw_record_fingerprint"])

    def test_exact_property_description_mappings(self):
        cases = {
            "Second-Hand Dwelling house /Apartment": ("second_hand_dwelling", False),
            "New Dwelling house /Apartment": ("new_dwelling", True),
            "Teach/?ras?n C?naithe Nua": ("new_dwelling", True),
            "Teach/\u00c1ras\u00e1n C\u00f3naithe Ath\u00e1imhe": ("second_hand_dwelling", False),
            "Teach/\u00c1ras\u00e1n C\u00f3naithe Nua": ("new_dwelling", True),
        }
        for raw_value, expected in cases.items():
            with self.subTest(raw_value=raw_value):
                normalized, method, is_new_build = map_property_description(raw_value)
                self.assertEqual(normalized, expected[0])
                self.assertEqual(method, "exact_source_value_mapping")
                self.assertEqual(is_new_build, expected[1])

    def test_unobserved_speculative_property_description_variant_is_not_mapped(self):
        normalized, method, is_new_build = map_property_description("Teach/\u00c3\u0081ras\u00c3\u00a1n C\u00c3\u00b3naithe Nua")
        self.assertEqual(normalized, "unknown")
        self.assertEqual(method, "unrecognised")
        self.assertTrue(pd.isna(is_new_build))

    def test_raw_field_preservation_for_confirmed_irish_and_mojibake_descriptions(self):
        rows = [
            self.row(description=description, address=f"Address {index}")
            for index, description in enumerate(CONFIRMED_IRISH_AND_MOJIBAKE_PROPERTY_DESCRIPTIONS)
        ]
        frame = self.transform(rows)
        for index, description in enumerate(CONFIRMED_IRISH_AND_MOJIBAKE_PROPERTY_DESCRIPTIONS):
            with self.subTest(description=description):
                self.assertEqual(frame.loc[index, "property_description_raw"], description)
                self.assertEqual(frame.loc[index, "source_raw__description_of_property"], description)
                self.assertEqual(frame.loc[index, "property_description_mapping_method"], "exact_source_value_mapping")

    def test_unrecognised_property_description_remains_unknown(self):
        normalized, method, is_new_build = map_property_description("Villa")
        self.assertEqual(normalized, "unknown")
        self.assertEqual(method, "unrecognised")
        self.assertTrue(pd.isna(is_new_build))

    def test_property_size_bucket_does_not_populate_floor_area(self):
        frame = self.transform(
            [
                self.row(
                    size="greater than or equal to 38 sq metres and less than 125 sq metres",
                )
            ]
        )
        self.assertEqual(
            frame.loc[0, "property_size_bucket_source"],
            "greater than or equal to 38 sq metres and less than 125 sq metres",
        )
        self.assertTrue(pd.isna(frame.loc[0, "floor_area_sqm"]))

    def test_checkpoint2_parquet_schema_and_row_count_validation(self):
        frame, validation, _ = self.transform_with_validation(
            [
                self.row(address="1 Parquet Road", vat="Yes", price="\u20ac100.00"),
                self.row(address="2 Parquet Road", eircode="", size="less than 38 sq metres"),
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint2.parquet"
            write_schema = write_checkpoint2_parquet(frame, validation.columns, path)
            read_schema = validate_checkpoint2_parquet(path, validation.columns, expected_row_count=2)
            self.assertEqual(write_schema, read_schema)
            self.assertEqual(read_schema, checkpoint2_arrow_schema(validation.columns))
            with self.assertRaises(PPRPhysicalSchemaError):
                validate_checkpoint2_parquet(path, validation.columns, expected_row_count=3)

    def test_baseline_unknown_type_and_area_fallback_evidence(self):
        rows = filter_training_rows(
            [
                {"transaction_date": "2024-01-01", "sale_price_eur": "1000000", "canonical_area": "Ranelagh", "property_type": "unknown"},
                {"transaction_date": "2024-02-01", "sale_price_eur": "1200000", "canonical_area": "Ranelagh", "property_type": "unknown"},
                {"transaction_date": "2024-03-01", "sale_price_eur": "1400000", "canonical_area": "Ranelagh", "property_type": "unknown"},
                {"transaction_date": "2024-04-01", "sale_price_eur": "900000", "canonical_area": "Ballsbridge", "property_type": "unknown"},
                {"transaction_date": "2024-05-01", "sale_price_eur": "950000", "canonical_area": "Ballsbridge", "property_type": "unknown"},
                {"transaction_date": "2024-06-01", "sale_price_eur": "990000", "canonical_area": "Ballsbridge", "property_type": "unknown"},
            ]
        )
        self.assertTrue(all(row["property_type"] == "unknown" for row in rows))
        model = GroupedMedianBaseline(min_group_support=3).fit(rows)
        prediction = model.predict_one({"canonical_area": "Ranelagh", "property_type": "Detached House"})
        self.assertEqual(prediction.backoff_level, "area")
        self.assertEqual(prediction.support_count, 3)

    def transform(self, rows, *, fieldnames=None, house_vat_rate=Decimal("0.135")):
        frame, _, _ = self.transform_with_validation(rows, fieldnames=fieldnames, house_vat_rate=house_vat_rate)
        return frame

    def transform_with_validation(self, rows, *, fieldnames=None, house_vat_rate=Decimal("0.135")):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ppr.csv"
            self.write_fixture(path, rows=rows, fieldnames=fieldnames)
            config = PPRSourceConfig(source_path=path, snapshot_date=date(2026, 6, 21), house_vat_rate=house_vat_rate)
            result = build_ppr_source_standardised_result(config)
            return result.frame, result.validation, result.source_file_sha256

    def write_fixture(self, path: Path, *, rows, encoding=PPR_ENCODING, fieldnames=None):
        fieldnames = fieldnames or REQUIRED_SOURCE_COLUMNS
        with path.open("w", encoding=encoding, newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    def row(
        self,
        *,
        date_text="01/01/2024",
        address="1 Main Street",
        county="Dublin",
        eircode="",
        price="\u20ac100,000.00",
        full_market="No",
        vat="No",
        description="Second-Hand Dwelling house /Apartment",
        size="",
        extra=None,
    ):
        output = {
            "Date of Sale (dd/mm/yyyy)": date_text,
            "Address": address,
            "County": county,
            "Eircode": eircode,
            PRICE_SOURCE_COLUMN: price,
            "Not Full Market Price": full_market,
            "VAT Exclusive": vat,
            "Description of Property": description,
            "Property Size Description": size,
        }
        if extra:
            output.update(extra)
        return output


if __name__ == "__main__":
    unittest.main()
