import math
import unittest

from house_valuation.data.filters import filter_training_rows
from house_valuation.inference.predict import confidence_from_support
from house_valuation.models.baseline import GroupedMedianBaseline


class BaselineTests(unittest.TestCase):
    def test_grouped_median_prefers_area_property_type(self):
        rows = filter_training_rows(
            [
                {"transaction_date": "2024-01-01", "sale_price_eur": "1000000", "canonical_area": "Ranelagh", "property_type": "Terraced House"},
                {"transaction_date": "2024-02-01", "sale_price_eur": "1200000", "canonical_area": "Ranelagh", "property_type": "Terraced House"},
                {"transaction_date": "2024-03-01", "sale_price_eur": "1400000", "canonical_area": "Ranelagh", "property_type": "Terraced House"},
            ]
        )
        model = GroupedMedianBaseline(min_group_support=2).fit(rows)
        prediction = model.predict_one({"canonical_area": "Ranelagh", "property_type": "Terraced House"})

        self.assertEqual(prediction.backoff_level, "area_property_type")
        self.assertAlmostEqual(prediction.predicted_price_eur, 1200000, delta=1)

    def test_confidence_thresholds(self):
        self.assertEqual(confidence_from_support(20, "area_property_type"), "normal_confidence")
        self.assertEqual(confidence_from_support(8, "area_property_type"), "low_confidence")
        self.assertEqual(confidence_from_support(4, "area"), "not_enough_comparable_support")


if __name__ == "__main__":
    unittest.main()

