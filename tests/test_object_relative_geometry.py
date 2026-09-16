import unittest
import numpy as np

from realitygraph.object_relative_geometry import subject_relative_geometry_features


class ObjectRelativeGeometryTests(unittest.TestCase):
    def _blob(self, shift_r=0.0, shift_c=0.0, scale=1.0):
        h, w = 32, 48
        rr, cc = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
        g = np.exp(-0.5 * (((rr-(15.0+shift_r))/3.0)**2 + ((cc-(23.0+shift_c))/7.0)**2))
        return scale * g

    def _bilateral_map(self, left, right=None):
        if right is None:
            right = left.copy()
        return np.concatenate([left, np.flip(right, axis=0)], axis=0)

    def test_positive_global_scale_does_not_change_representation(self):
        m = self._bilateral_map(self._blob())
        a, names, families = subject_relative_geometry_features(m[None])
        b, names2, families2 = subject_relative_geometry_features((7.5*m)[None])
        self.assertEqual(names, names2)
        self.assertEqual(families, families2)
        self.assertTrue(np.allclose(a, b, atol=1e-6, rtol=1e-6))

    def test_shared_translation_is_removed_by_intrinsic_frame(self):
        m0 = self._bilateral_map(self._blob())
        m1 = self._bilateral_map(self._blob(shift_r=3.0, shift_c=-4.0))
        a, names, _ = subject_relative_geometry_features(np.stack([m0, m1]))
        keep = [i for i, n in enumerate(names) if not n.startswith('frame_')]
        self.assertLess(float(np.mean(np.abs(a[0, keep] - a[1, keep]))), 0.03)

    def test_symmetric_bilateral_map_has_zero_asymmetry(self):
        m = self._bilateral_map(self._blob())
        a, names, _ = subject_relative_geometry_features(m[None])
        asym = [i for i, n in enumerate(names) if n.startswith('asym_')]
        self.assertGreater(len(asym), 10)
        self.assertLess(float(np.max(np.abs(a[0, asym]))), 1e-8)

    def test_localized_right_depletion_changes_intrinsic_asymmetry(self):
        left = self._blob()
        right = left.copy()
        right[:, 24:] *= 0.45
        m = self._bilateral_map(left, right)
        a, names, _ = subject_relative_geometry_features(m[None])
        idx = names.index('asym_f70_longitudinal_centroid')
        self.assertGreater(abs(float(a[0, idx])), 0.01)


if __name__ == '__main__':
    unittest.main()
