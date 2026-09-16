import unittest
import numpy as np

from realitygraph.threshold_trajectory import (
    curve_features,
    dense_threshold_trajectory_features,
)


class ThresholdTrajectoryTests(unittest.TestCase):
    def test_linear_curve_has_zero_curvature_and_positive_slope(self):
        t = np.arange(0.40, 0.81, 0.05)
        v = 2.0 * t + 1.0
        values, names = curve_features(v, t, prefix='x')
        got = dict(zip(names, values))
        self.assertAlmostEqual(got['x_slope'], 2.0, places=8)
        for name, value in got.items():
            if '_curv_' in name:
                self.assertAlmostEqual(value, 0.0, places=8)

    def test_dense_bank_is_finite_deterministic_and_subject_relative(self):
        rr, cc = np.meshgrid(np.linspace(-1, 1, 32), np.linspace(-1, 1, 64), indexing='ij')
        left = np.exp(-((rr / 0.35) ** 2 + ((cc + 0.45) / 0.22) ** 2))
        right = 0.85 * np.exp(-((rr / 0.32) ** 2 + ((cc - 0.45) / 0.24) ** 2))
        image = left + right
        maps = np.stack([image, 1.7 * image], axis=0)
        X1, names1, families1 = dense_threshold_trajectory_features(maps)
        X2, names2, families2 = dense_threshold_trajectory_features(maps)
        self.assertEqual(X1.shape[0], 2)
        self.assertGreater(X1.shape[1], 300)
        self.assertTrue(np.isfinite(X1).all())
        np.testing.assert_allclose(X1, X2, atol=0.0, rtol=0.0)
        self.assertEqual(names1, names2)
        self.assertEqual(families1, families2)
        self.assertIn('right_mean_uptake_delta_50_55', names1)
        self.assertIn('mean_long_mass_q10_curv_60', names1)
        self.assertIn('right_mean_uptake_auc', names1)
        # q90 scaling makes the representation invariant to positive global scale.
        np.testing.assert_allclose(X1[0], X1[1], atol=1e-9, rtol=1e-9)


if __name__ == '__main__':
    unittest.main()
