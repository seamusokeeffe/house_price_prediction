import csv
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import pyarrow as pa

from house_valuation.data.geography_mapping import (
    Checkpoint3PhysicalSchemaError,
    GeographyConfigError,
    GeographyMapper,
    checkpoint3_arrow_schema,
    enrich_with_geography,
    load_canonical_aliases,
    load_manual_overrides,
    validate_checkpoint3_parquet,
    write_checkpoint3_parquet,
)


CONFIG_PATH = Path("config/canonical_areas.csv")
OVERRIDES_PATH = Path("config/address_overrides.csv")


class GeographyMappingTests(unittest.TestCase):
    def setUp(self):
        self.aliases = load_canonical_aliases(CONFIG_PATH)
        self.mapper = GeographyMapper(self.aliases)

    def test_exact_canonical_safe_alias_and_scopes(self):
        frame = self.enrich(
            [
                self.row("1 Main Street, Ranelagh, Dublin 6"),
                self.row("2 Village Road, Harold's Cross, Dublin 6W"),
                self.row("3 Coast Road, Monkstown, Co Dublin"),
            ]
        )
        self.assertEqual(frame.loc[0, "canonical_area"], "Ranelagh")
        self.assertEqual(frame.loc[0, "geo_scope"], "inference")
        self.assertEqual(frame.loc[1, "canonical_area"], "Harolds Cross")
        self.assertEqual(frame.loc[1, "geo_scope"], "training_only")
        self.assertEqual(frame.loc[2, "canonical_area"], "Monkstown")
        self.assertEqual(frame.loc[2, "geo_scope"], "inference")

    def test_accented_and_unaccented_dun_laoghaire(self):
        frame = self.enrich(
            [
                self.row("10 Marine Road, Dún Laoghaire", county="Dublin"),
                self.row("11 Marine Road, Dun Laoghaire", county="Dublin"),
            ]
        )
        self.assertEqual(frame["canonical_area"].tolist(), ["Dún Laoghaire", "Dún Laoghaire"])
        self.assertTrue((frame["geo_scope"] == "training_only").all())

    def test_unmatched_and_out_of_scope(self):
        frame = self.enrich(
            [
                self.row("1 Unknown Road, Dublin", county="Dublin"),
                self.row("1 Church Street, Galway", county="Galway"),
            ]
        )
        self.assertEqual(frame.loc[0, "geography_match_status"], "unmatched")
        self.assertEqual(frame.loc[0, "geo_scope"], "unknown")
        self.assertEqual(frame.loc[1, "geography_match_status"], "unmatched")
        self.assertEqual(frame.loc[1, "geo_scope"], "out_of_scope")

    def test_multiple_candidate_areas_are_ambiguous(self):
        frame = self.enrich([self.row("1 Border Road, Ranelagh, Rathmines, Dublin 6")])
        self.assertEqual(frame.loc[0, "geography_match_status"], "ambiguous")
        self.assertEqual(frame.loc[0, "geography_candidate_areas"], "Ranelagh|Rathmines")

    def test_priority_resolves_mount_merrion_over_merrion(self):
        frame = self.enrich([self.row("5 Sycamore Crescent, Mount Merrion, County Dublin")])
        self.assertEqual(frame.loc[0, "canonical_area"], "Mount Merrion")
        self.assertEqual(frame.loc[0, "geography_match_priority"], 10)

    def test_token_boundaries_postal_district_and_broad_authority(self):
        frame = self.enrich(
            [
                self.row("1 Blackrocket Road, Dublin", county="Dublin"),
                self.row("Dublin 4", county="Dublin"),
                self.row("Dún Laoghaire-Rathdown", county="Dublin"),
            ]
        )
        self.assertTrue(pd.isna(frame.loc[0, "canonical_area"]))
        self.assertEqual(frame.loc[1, "geography_match_status"], "unmatched")
        self.assertIn("broad_dublin_reference_only", frame.loc[1, "geography_quality_flags"])
        self.assertTrue(pd.isna(frame.loc[2, "canonical_area"]))

    def test_mount_merrion_is_not_mapped_to_merrion(self):
        frame = self.enrich([self.row("5 Sycamore Crescent, Mount Merrion, Dublin")])
        self.assertEqual(frame.loc[0, "canonical_area"], "Mount Merrion")

    def test_non_dublin_duplicate_locality_is_not_mapped_and_conflict_flagged(self):
        frame = self.enrich([self.row("21 Richmond Estate, Blackrock", county="Cork")])
        self.assertTrue(pd.isna(frame.loc[0, "canonical_area"]))
        self.assertIn("conflicting_county_context", frame.loc[0, "geography_quality_flags"])

    def test_county_context_conflict_is_flagged(self):
        frame = self.enrich([self.row("1 Main Street, Ranelagh", county="Galway")])
        self.assertEqual(frame.loc[0, "geo_scope"], "out_of_scope")
        self.assertIn("conflicting_county_context", frame.loc[0, "geography_quality_flags"])

    def test_manual_override_takes_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            override_path = Path(directory) / "overrides.csv"
            self.write_overrides(override_path, [{"record_id": "r1", "canonical_area": "Ranelagh", "geo_scope": "inference"}])
            frame = enrich_with_geography(
                pd.DataFrame([self.row("1 Unknown Road, Galway", county="Galway", record_id="r1")]),
                canonical_areas_path=CONFIG_PATH,
                overrides_path=override_path,
            )
            self.assertEqual(frame.loc[0, "geography_match_status"], "manual_override")
            self.assertEqual(frame.loc[0, "canonical_area"], "Ranelagh")

    def test_invalid_override_area_conflict_and_scope_mismatch_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            unknown_path = directory_path / "unknown.csv"
            self.write_overrides(unknown_path, [{"record_id": "r1", "canonical_area": "Not Real", "geo_scope": "inference"}])
            with self.assertRaises(GeographyConfigError):
                load_manual_overrides(unknown_path, self.aliases)

            conflict_path = directory_path / "conflict.csv"
            self.write_overrides(
                conflict_path,
                [
                    {"record_id": "r1", "canonical_area": "Ranelagh", "geo_scope": "inference"},
                    {"record_id": "r1", "canonical_area": "Kimmage", "geo_scope": "training_only"},
                ],
            )
            with self.assertRaises(GeographyConfigError):
                load_manual_overrides(conflict_path, self.aliases)

            mismatch_path = directory_path / "mismatch.csv"
            self.write_overrides(mismatch_path, [{"record_id": "r1", "canonical_area": "Kimmage", "geo_scope": "inference"}])
            with self.assertRaises(GeographyConfigError):
                load_manual_overrides(mismatch_path, self.aliases)

    def test_pipeline_schema_row_count_preservation_and_determinism(self):
        source = pd.DataFrame(
            [
                {"record_id": "r1", "raw_address": "1 Main Street, Ranelagh, Dublin", "county_raw": "Dublin", "eircode_raw": "", "transaction_year": 2024},
                {"record_id": "r2", "raw_address": "1 Main Street, Cork", "county_raw": "Cork", "eircode_raw": "", "transaction_year": 2024},
            ]
        )
        first = enrich_with_geography(source, canonical_areas_path=CONFIG_PATH, overrides_path=OVERRIDES_PATH)
        second = enrich_with_geography(source, canonical_areas_path=CONFIG_PATH, overrides_path=OVERRIDES_PATH)
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(len(first), len(source))
        self.assertEqual(first["record_id"].tolist(), source["record_id"].tolist())
        for column in source.columns:
            self.assertIn(column, first.columns)

        input_schema = pa.schema(
            [
                pa.field("record_id", pa.string(), nullable=False),
                pa.field("raw_address", pa.string(), nullable=False),
                pa.field("county_raw", pa.string(), nullable=False),
                pa.field("eircode_raw", pa.string(), nullable=True),
                pa.field("transaction_year", pa.int64(), nullable=True),
            ]
        )
        schema = checkpoint3_arrow_schema(input_schema)
        self.assertIn("canonical_area", schema.names)
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "geo.parquet"
            write_checkpoint3_parquet(first, input_schema, output_path)
            read_schema = validate_checkpoint3_parquet(output_path, input_schema, expected_row_count=2)
            self.assertEqual(read_schema.remove_metadata(), schema.remove_metadata())
            with self.assertRaises(Checkpoint3PhysicalSchemaError):
                validate_checkpoint3_parquet(output_path, input_schema, expected_row_count=3)

    def test_no_training_or_property_scope_fields_are_introduced(self):
        frame = self.enrich([self.row("1 Main Street, Ranelagh, Dublin")])
        prohibited = {"exclude_from_training", "exclusion_reason", "is_possible_multi_property_sale", "single_dwelling_confidence"}
        self.assertFalse(prohibited.intersection(frame.columns))

    def enrich(self, rows):
        return enrich_with_geography(pd.DataFrame(rows), canonical_areas_path=CONFIG_PATH, overrides_path=OVERRIDES_PATH)

    def row(self, address, *, county="Dublin", record_id="r", eircode=""):
        return {
            "record_id": record_id,
            "raw_address": address,
            "county_raw": county,
            "eircode_raw": eircode,
            "transaction_year": 2024,
        }

    def write_overrides(self, path: Path, rows):
        fieldnames = ["record_id", "canonical_area", "geo_scope", "override_reason", "reviewed_by", "review_date", "notes"]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                full = {
                    "override_reason": "test",
                    "reviewed_by": "unit_test",
                    "review_date": "2026-06-21",
                    "notes": "",
                }
                full.update(row)
                writer.writerow(full)


if __name__ == "__main__":
    unittest.main()
