import unittest

import numpy as np

from realitygraph.invariant_3d import (
    bilateral_channels,
    downsample_mean3d,
    group_dro_weights,
    robust_views,
)


class Invariant3DContractTests(unittest.TestCase):
    def test_robust_views_are_scale_invariant_and_finite(self):
        v = np.zeros((8, 8, 8), dtype=np.float32)
        v[1:7, 1:7, 1:7] = np.linspace(1.0, 9.0, 6 * 6 * 6, dtype=np.float32).reshape(6, 6, 6)
        x1, r1 = robust_views(v)
        x2, r2 = robust_views(v * 7.0)
        self.assertTrue(np.isfinite(x1).all())
        self.assertTrue(np.isfinite(r1).all())
        np.testing.assert_allclose(x1, x2, atol=1e-6)
        np.testing.assert_allclose(r1, r2, atol=1e-6)

    def test_bilateral_channels_make_symmetric_absdiff_zero(self):
        rng = np.random.default_rng(7)
        left = rng.normal(size=(4, 6, 8)).astype(np.float32)
        symmetric = np.concatenate([left, np.flip(left, axis=0)], axis=0)
        channels = bilateral_channels(symmetric, 2.0 * symmetric)
        self.assertEqual(channels.shape, (8, 4, 6, 8))
        np.testing.assert_allclose(channels[3], 0.0, atol=1e-7)
        np.testing.assert_allclose(channels[7], 0.0, atol=1e-7)

    def test_downsample_mean3d_preserves_channel_means(self):
        a = np.arange(2 * 4 * 6 * 8, dtype=np.float32).reshape(2, 4, 6, 8)
        b = downsample_mean3d(a, factor=2)
        self.assertEqual(b.shape, (2, 2, 3, 4))
        np.testing.assert_allclose(a.mean(axis=(1, 2, 3)), b.mean(axis=(1, 2, 3)), atol=1e-6)

    def test_group_dro_weights_focus_on_higher_loss_environment(self):
        previous = np.ones(3, dtype=np.float64) / 3.0
        weights = group_dro_weights(previous, np.array([0.2, 0.5, 0.1]), eta=0.5)
        self.assertAlmostEqual(float(weights.sum()), 1.0, places=12)
        self.assertEqual(int(np.argmax(weights)), 1)
        self.assertTrue((weights > 0).all())


if __name__ == "__main__":
    unittest.main()
