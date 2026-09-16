import unittest

import numpy as np

from realitygraph.capacity_control_sweep import (
    CONTROL_FAMILIES,
    LOW_RANK_SIZES,
    regional_pool_numpy,
    spatial_pyramid_numpy,
    total_variation_numpy,
)


class CapacityControlSweepTests(unittest.TestCase):
    def test_all_five_capacity_controls_are_present(self):
        self.assertEqual(
            CONTROL_FAMILIES,
            ("lowrank", "regional", "attention", "pyramid", "sparse_tv"),
        )
        self.assertEqual(LOW_RANK_SIZES, (4, 8, 16, 32, 64))

    def test_regional_pool_preserves_multiple_spatial_regions(self):
        x = np.arange(2 * 4 * 8 * 8, dtype=float).reshape(2, 4, 8, 8)
        pooled = regional_pool_numpy(x)
        self.assertEqual(pooled.shape, (2, 8))
        self.assertFalse(np.allclose(pooled[:, 0], pooled[:, -1]))

    def test_spatial_pyramid_keeps_coarse_and_fine_descriptors(self):
        x = np.arange(2 * 4 * 8 * 8, dtype=float).reshape(2, 4, 8, 8)
        pyramid = spatial_pyramid_numpy(x)
        self.assertEqual(pyramid.shape[0], 2)
        self.assertGreater(pyramid.shape[1], 8)

    def test_total_variation_is_zero_for_constant_map_and_positive_for_edge(self):
        const = np.ones((4, 8, 8), dtype=float)
        edge = const.copy()
        edge[:, :, 4:] = 2.0
        self.assertEqual(total_variation_numpy(const), 0.0)
        self.assertGreater(total_variation_numpy(edge), 0.0)


if __name__ == "__main__":
    unittest.main()
