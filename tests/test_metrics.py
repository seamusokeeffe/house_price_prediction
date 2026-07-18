import unittest

from house_valuation.evaluation.metrics import mae_eur, median_absolute_percentage_error


class MetricsTests(unittest.TestCase):
    def test_mae_eur(self):
        self.assertEqual(mae_eur([100.0, 200.0], [110.0, 180.0]), 15.0)

    def test_median_absolute_percentage_error(self):
        result = median_absolute_percentage_error([100.0, 200.0], [110.0, 180.0])
        self.assertAlmostEqual(result, 0.1)


if __name__ == "__main__":
    unittest.main()

