import unittest

from realitygraph.geometry_core_contraction import (
    greedy_contract,
    removal_ablation,
)


class GeometryCoreContractionTests(unittest.TestCase):
    def test_greedy_contract_deletes_dispensible_features_without_losing_consequence(self):
        losses = {
            (0, 1, 2): 0.3000,
            (0, 1): 0.3000,
            (0, 2): 0.3120,
            (1, 2): 0.3350,
            (0,): 0.3010,
            (1,): 0.3500,
            (2,): 0.4100,
        }

        def score(features):
            return losses[tuple(features)]

        result = greedy_contract((0, 1, 2), score, tolerance=0.0015)
        self.assertEqual(result['features'], (0,))
        self.assertAlmostEqual(result['loss'], 0.3010)
        self.assertEqual(result['removed'], (2, 1))

    def test_removal_ablation_reports_harm_of_each_retained_feature(self):
        losses = {
            (0, 1): 0.300,
            (0,): 0.314,
            (1,): 0.341,
        }

        def score(features):
            return losses[tuple(features)]

        rows = removal_ablation((0, 1), score)
        self.assertEqual(rows[0]['feature'], 0)
        self.assertAlmostEqual(rows[0]['harm'], 0.041)
        self.assertEqual(rows[1]['feature'], 1)
        self.assertAlmostEqual(rows[1]['harm'], 0.014)


if __name__ == '__main__':
    unittest.main()
