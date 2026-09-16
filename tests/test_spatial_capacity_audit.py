import unittest
import numpy as np

from realitygraph.spatial_capacity_audit import environment_label_folds


class SpatialCapacityAuditTests(unittest.TestCase):
    def test_environment_label_folds_cover_each_row_once(self):
        env = np.repeat(np.arange(3), 20)
        y = np.tile(np.array([0, 1] * 10), 3)
        folds = environment_label_folds(env, y, n_splits=5, seed=7)
        self.assertEqual(folds.shape, (60,))
        self.assertTrue(np.all((folds >= 0) & (folds < 5)))
        for e in range(3):
            for label in (0, 1):
                idx = np.flatnonzero((env == e) & (y == label))
                counts = np.bincount(folds[idx], minlength=5)
                self.assertLessEqual(int(counts.max() - counts.min()), 1)


if __name__ == '__main__':
    unittest.main()
