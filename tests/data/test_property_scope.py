"""Tests for conservative PPR property-scope assessment."""

import unittest

import pandas as pd

from house_valuation.data.property_scope import assess_property_scope


class PropertyScopeTests(unittest.TestCase):
    """Verify explicit exclusions and unresolved eligibility evidence."""

    def test_explicit_apartment_flat_and_apt_are_non_house(self):
        """Classify explicit apartment evidence without changing source types."""

        frame = pd.DataFrame({
            "address_normalized": [
                "APARTMENT 2 TEST COURT", "FLAT 3 TEST HOUSE", "APT. 4 TEST COURT"
            ],
            "property_type": ["unknown"] * 3,
            "property_type_source": ["unknown"] * 3,
            "property_type_quality_flag": ["ppr_house_apartment_ambiguous"] * 3,
        })
        result = assess_property_scope(frame)
        self.assertTrue(result["property_scope_status"].eq("clearly_non_house").all())
        pd.testing.assert_series_equal(result["property_type"], frame["property_type"])
        pd.testing.assert_series_equal(result["property_type_source"], frame["property_type_source"])

    def test_ambiguous_unit_is_review_and_absence_is_unresolved(self):
        """Keep UNIT evidence under review and never infer a house by absence."""

        result = assess_property_scope(pd.DataFrame({
            "address_normalized": ["UNIT 4 TEST COURT", "4 TEST ROAD", "CAPTAIN'S HOUSE"]
        }))
        self.assertEqual(result.loc[0, "property_scope_status"], "review_required")
        self.assertEqual(result.loc[1, "property_scope_status"], "unresolved_house_or_apartment")
        self.assertEqual(result.loc[2, "property_scope_status"], "unresolved_house_or_apartment")
        self.assertNotEqual(result.loc[1, "property_scope_status"], "house")


if __name__ == "__main__":
    unittest.main()
